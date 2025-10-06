import math
import time
import typing as t
from collections.abc import Callable

from ..utils import pipe
from ..utils.result import Err, Ok, Result
from .redis_setup import (
  acquire_lock,
  get_json,
  release_lock,
  set_json,
)

# tuning defaults
DEFAULT_CACHE_TTL = 300  # 5 minutes
LOCK_TTL = 10  # seconds the lock holds
LOCK_WAIT_TIMEOUT = 3.0  # seconds to poll for cached value
LOCK_POLL_INTERVAL = 0.05  # polling interval (s)
MAX_RESULTS_IN_BUCKET = 20


def lat_lon_decimals_for_radius(
  latitude: float, radius_m: float
) -> tuple[int, int]:
  """Return (lat_decimals, lon_decimals) for rounding so thatso each grid cell is smaller than radius_m."""  # noqa: E501
  if radius_m <= 0:
    # This is the default if the radius is 0,
    # It will act like a fallback creating point-level buckets
    return (6, 6)

  meters_per_deg_lat = 111000.0
  lat_frac = 2.0 * radius_m / meters_per_deg_lat
  lat_n_decimals = math.ceil(-math.log10(lat_frac)) if lat_frac < 1 else 0

  lat_rad = math.radians(latitude)
  meters_per_deg_lon = max(1.0, 111000.0 * math.cos(lat_rad))
  lon_frac = 2.0 * radius_m / meters_per_deg_lon
  lon_n_decimals = math.ceil(-math.log10(lon_frac)) if lon_frac < 1 else 0

  return max(0, lat_n_decimals), max(0, lon_n_decimals)


def build_region_key(latitude: float, longitude: float, radius: float) -> str:
  """
  Build a deterministic cache key using rounded lat/lon buckets and radius.
  """
  # Not sure if we need to include any other params in the cache key
  lat_n_decimals, lon_n_decimals = lat_lon_decimals_for_radius(latitude, radius)
  lat_bucket = f"{round(latitude, lat_n_decimals):.{lat_n_decimals}f}"
  lon_bucket = f"{round(longitude, lon_n_decimals):.{lon_n_decimals}f}"

  return f"search_nearby:lat={lat_bucket}:lon={lon_bucket}:radius={radius}"  # noqa: E501


def haversine_distance_m(
  lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
  """Return distance in meters between two lat/lon points (Haversine)."""
  earth_radius = 6371000.0  # Earth radius in meters
  phi1, phi2 = math.radians(lat1), math.radians(lat2)
  lat_diff = phi2 - phi1
  lon_diff = math.radians(lon2 - lon1)
  haversine_of_central_angle = (
    math.sin(lat_diff / 2) ** 2
    + math.cos(phi1) * math.cos(phi2) * math.sin(lon_diff / 2) ** 2
  )
  # converting angular distance to linear distance
  return 2 * earth_radius * math.asin(math.sqrt(haversine_of_central_angle))


def fetch_or_cache_region(
  *,
  latitude: float,
  longitude: float,
  radius: float,
  caller: Callable[[], dict[str, t.Any]],
  max_results: int = MAX_RESULTS_IN_BUCKET,
  cache_ttl: int = DEFAULT_CACHE_TTL,
  lock_ttl: int = LOCK_TTL,
  wait_timeout: float = LOCK_WAIT_TIMEOUT,
  poll_interval: float = LOCK_POLL_INTERVAL,
  filter_by_distance: bool = True,
) -> Result[dict[str, t.Any], str]:
  """
  Generic helper:
  - build cache key
  - return cached response if present
  - otherwise acquire lock, call `fetcher()`, cache the result and return it
  - if lock lost, poll for result briefly then fallback to calling fetcher
  """

  # Not sure if we need to optionally filter places
  # by exact haversine distance before returning

  cache_key = build_region_key(latitude, longitude, radius)

  # try cached value using helper
  cached_result = get_json(cache_key)
  match cached_result:
    case Ok(payload):
      print(f"\n[DEBUG-REDIS-CACHING] Cache hit for key: {cache_key}\n")
      if filter_by_distance:
        payload = _filter_payload_by_radius(
          payload, latitude, longitude, radius
        )
      return Ok(payload)
    case Err(e):
      # Cache miss or error, continue to fetch
      print(f"\n[DEBUG-REDIS-CACHING] Cache miss: {e}\n")
      pass

  # If there is no cached value, we try to acquire the lock and populate cache
  lock_result = acquire_lock(cache_key, ttl=lock_ttl)
  match lock_result:
    case Ok(token):
      try:
        payload = caller()
        # Use pipe for functional composition
        payload = pipe(
          payload,
          lambda p: _filter_payload_by_radius(p, latitude, longitude, radius)
          if filter_by_distance
          else p,
          lambda p: {**p, "places": p["places"][:max_results]}
          if isinstance(p.get("places"), list)
          else p,
        )
        # Cache the result using helper
        cache_result = set_json(cache_key, payload, expire_seconds=cache_ttl)
        match cache_result:
          case Ok(_):
            print(
              f"\n[DEBUG-REDIS-CACHING] Successfully cached data for key: {cache_key}\n"  # noqa: E501
            )
            return Ok(payload)
          case Err(e):
            return Err(f"Failed to cache data: {e}")
      except Exception as e:
        return Err(f"Failed to fetch data: {e}")
      finally:
        # Release lock using helper
        _ = release_lock(cache_key, token)
    case Err(e):
      # Could not acquire lock, continue to polling
      # Could log: print(f"Could not acquire lock: {e}")
      pass

  # If we didn't get the lock, we poll for the cached value
  waited = 0.0
  while waited < wait_timeout:
    time.sleep(poll_interval)
    waited += poll_interval
    cached_result = get_json(cache_key)
    match cached_result:
      case Ok(payload):
        print(
          f"\n[DEBUG-REDIS-CACHING] Polling cache hit for key: {cache_key}\n"
        )
        if filter_by_distance:
          payload = _filter_payload_by_radius(
            payload, latitude, longitude, radius
          )
        return Ok(payload)
      case Err(e):
        print(f"\n[DEBUG-REDIS-CACHING] Polling cache miss: {e}\n")
        continue

  # Might not need this but just in case as our ultimate fallback,
  # We call the caller ourselves
  try:
    payload = caller()
    if filter_by_distance:
      payload = _filter_payload_by_radius(payload, latitude, longitude, radius)
    # Cache the fallback result
    cache_result = set_json(cache_key, payload, expire_seconds=cache_ttl)
    match cache_result:
      case Ok(_):
        print(
          f"\n[DEBUG-REDIS-CACHING] WARNING: cached via fallback data for key: {cache_key}\n"  # noqa: E501
        )
        return Ok(payload)
      case Err(e):
        return Err(f"Failed to cache fallback data: {e}")
  except Exception as e:
    return Err(f"Fallback fetch failed: {e}")


def _filter_payload_by_radius(
  payload: dict[str, t.Any], lat: float, lon: float, radius_m: float
) -> dict[str, t.Any]:
  """
  Expect payload like {"places":[{"latitude":..., "longitude":..., ...}, ...]}
  Filter out places outside radius_m (Haversine).
  """
  if not payload or "places" not in payload:
    return payload
  filtered: list[t.Any] = []
  for place in payload["places"]:
    try:
      haversine_distance = haversine_distance_m(
        lat, lon, float(place["latitude"]), float(place["longitude"])
      )
      if haversine_distance <= radius_m:
        filtered.append(place)
    except Exception:
      # if any parsing fails, keep the place (fail-open)
      filtered.append(place)
  return {"places": filtered}
