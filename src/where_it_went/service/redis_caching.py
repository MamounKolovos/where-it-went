import math
import time
import typing as t
from collections.abc import Callable
from typing import Any

import s2cell  # pyright: ignore[reportMissingTypeStubs]

from where_it_went.service.redis_setup import (
  acquire_lock,
  get_json,
  release_lock,
  set_json,
)
from where_it_went.utils.result import Err, Ok, Result

# tuning defaults
DEFAULT_CACHE_TTL = 300  # 5 minutes
LOCK_TTL = 10  # seconds the lock holds
LOCK_WAIT_TIMEOUT = 3.0  # seconds to poll for cached value
LOCK_POLL_INTERVAL = 0.05  # polling interval (s)
MAX_RECURSION_LEVEL = 17
MAX_S2_LEVEL = 24
MIN_S2_LEVEL = 10


LEVEL_TO_DIAMETER: dict[int, float] = {
  24: 0.6,
  23: 1.2,
  22: 2.4,
  21: 4.8,
  20: 9.5,
  19: 19.0,
  18: 38.0,
  17: 76.0,
  16: 153.0,
  15: 305.0,
  14: 610.0,
  13: 1220.0,
  12: 2441.0,
  11: 4883.0,
  10: 9766.0,
}


def choose_s2_level_for_radius(radius_m: float) -> int:
  """
  Choose a reasonable S2 level for `radius_m`.
  Strategy (conservative):
  - Return the smallest numeric level whose approx diameter
    is >= radius_m. That means the chosen cell size is >= query radius
  - If radius is extremely large, return MIN_S2_LEVEL.
  Notes:
  - As of now, I'm just using LEVEL_TO_DIAMETER as a simple heuristic.
  """
  if radius_m <= 0:
    return MAX_S2_LEVEL
  for level, approx_diam in LEVEL_TO_DIAMETER.items():
    if approx_diam >= radius_m:
      return level

  # Fallback when all mapped diameters are < radius_m
  return MIN_S2_LEVEL


def build_region_key_s2(
  latitude: float,
  longitude: float,
  radius_m: float,
  s2_level: int | None = None,
) -> str:
  """
  Build an S2-cell-based cache key and return (cache_key, used_level).
  If `s2_level` is None, choose one automatically based on radius using
  `choose_s2_level_for_radius`.
  Cache key format: search_nearby:cell=<token>:lvl=<level>
  """
  level = (
    s2_level if s2_level is not None else choose_s2_level_for_radius(radius_m)
  )
  # clamp level to valid range
  level = max(MIN_S2_LEVEL, min(level, MAX_S2_LEVEL))
  token = s2cell.lat_lon_to_token(latitude, longitude, level=level)
  return token


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


def get_child_cell_ids(cell_id: int) -> list[int]:
  """Return 4 child cell IDs of the given parent cell."""
  # Each S2 cell has 4 children, represented by the next level bits.
  child_level = s2cell.cell_id_to_level(cell_id) + 1
  if child_level > MAX_S2_LEVEL:
    return []
  children = []
  # The child cell IDs are contiguous in the S2 space
  # (parent_id << 2) gives you the first child, next 3 are sequential
  first_child = cell_id << 2
  children = [first_child + i for i in range(4)]
  return children


# TODO : Use search_nearby instead of caller in fetch_or_cache_region
def fetch_and_merge_child_cells(
  cache_key: str,
  radius: float,
  caller: Callable[[float, float, float], dict[str, Any]],
  cache_ttl: int = DEFAULT_CACHE_TTL,
) -> dict[str, Any]:
  """
  For a parent S2 cell key, try to fetch cached data for child cells,
  merge them, and fetch from API if children are missing.
  Returns a merged payload with "places".
  """

  merged_payload: dict[str, Any] = {"places": []}
  parent_cell_id = s2cell.token_to_cell_id(cache_key)
  current_recursion_level = s2cell.cell_id_to_level(parent_cell_id)

  # If we've hit max recursion level, fetch data directly for this cell
  if current_recursion_level >= MAX_RECURSION_LEVEL:
    cell_center_lat, cell_center_lon = s2cell.token_to_lat_lon(cache_key)
    radius = LEVEL_TO_DIAMETER[current_recursion_level] / 2
    payload = caller(cell_center_lat, cell_center_lon, radius)
    cache_result = set_json(cache_key, payload, expire_seconds=cache_ttl)
    match cache_result:
      case Ok(_):
        print(
          f"\n[DEBUG-REDIS-CACHING] Successfully cached data for key: {cache_key}\n"  # noqa: E501
        )
      case Err(e):
        print(
          f"\n[DEBUG-REDIS-CACHING] Failed to cache data for key: {cache_key}: {e}\n"  # noqa: E501
        )
    return payload

  child_cell_ids = get_child_cell_ids(parent_cell_id)

  for child_cell_id in child_cell_ids:
    child_token = s2cell.cell_id_to_token(child_cell_id)
    cached_result: Result[dict[str, Any], str] = get_json(child_token)

    match cached_result:
      case Ok(payload):
        print(
          f"\n[DEBUG-REDIS-CACHING] Cache hit for child cell: {child_token}\n"
        )  # noqa: E501
        merged_payload["places"].extend(payload.get("places", []))
      case Err(_):
        # Recursively fetch child data and cache it
        try:
          child_payload = fetch_and_merge_child_cells(
            child_token, radius, caller, cache_ttl
          )
        except Exception as e:
          print(
            f"[DEBUG-REDIS-CACHING] Child fetch failed for {child_token}: {e}"
          )
          continue
        merged_payload["places"].extend(child_payload.get("places", []))

        # Cache the recursively fetched data to avoid future API calls
        cache_result = set_json(
          child_token, child_payload, expire_seconds=cache_ttl
        )
        match cache_result:
          case Ok(_):
            print(
              f"\n[DEBUG-REDIS-CACHING] Cached recursively fetched data for: {child_token}\n"  # noqa: E501
            )
          case Err(e):
            print(
              f"\n[DEBUG-REDIS-CACHING] Failed to cache recursively fetched data for {child_token}: {e}\n"  # noqa: E501
            )

  # Fallback: if no child data found, fetch for parent cell
  if not merged_payload["places"]:
    cell_center_lat, cell_center_lon = s2cell.token_to_lat_lon(cache_key)
    payload = caller(cell_center_lat, cell_center_lon, radius)
    merged_payload["places"].extend(payload.get("places", []))

  return merged_payload


def fetch_or_cache_region(
  *,
  latitude: float,
  longitude: float,
  radius: float,
  caller: Callable[[float, float, float], dict[str, t.Any]],
  cache_ttl: int = DEFAULT_CACHE_TTL,
  lock_ttl: int = LOCK_TTL,
  wait_timeout: float = LOCK_WAIT_TIMEOUT,
  poll_interval: float = LOCK_POLL_INTERVAL,
  filter_by_distance: bool = True,
) -> Result[dict[str, t.Any], str]:
  """
    Behavior summary:
  - First building an S2 token cache key using build_region_key_s2
  - Try cached value for the exact cell.
  - If not found and `search_parent_levels>0`, probe parent cells (coarser)
    in ascending coarseness — this enables hierarchical cache reuse.
  - Otherwise, try acquire_lock + populate cache as before.
  - After reading cached payload, we still apply exact-radius filtering using
    _filter_payload_by_radius (unchanged).
  """

  # Not sure if we need to optionally filter places
  # by exact haversine distance before returning

  cache_key = build_region_key_s2(latitude, longitude, radius)

  # try cached value using helper
  cached_result = get_json(cache_key)
  match cached_result:
    case Ok(payload):
      print(f"\n[DEBUG-REDIS-CACHING] Cache hit for key: {cache_key}\n")
      if filter_by_distance:
        payload = filter_payload_by_radius(payload, latitude, longitude, radius)
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
        merged_payload = fetch_and_merge_child_cells(
          cache_key, radius, caller, cache_ttl
        )
        cache_result = set_json(
          cache_key, merged_payload, expire_seconds=cache_ttl
        )
        match cache_result:
          case Ok(_):
            print(
              f"\n[DEBUG-REDIS-CACHING] Successfully cached data for key: {cache_key}\n"  # noqa: E501
            )
            if filter_by_distance:
              merged_payload = filter_payload_by_radius(
                merged_payload, latitude, longitude, radius
              )
            return Ok(merged_payload)
          case Err(e):
            return Err(
              f"[DEBUG-REDIS-CACHING] Failed to cache data for key: {cache_key}: {e}"  # noqa: E501
            )  # noqa: E501
      except Exception as e:
        return Err(
          f"[DEBUG-REDIS-CACHING] Failed to fetch data for key: {cache_key}: {e}"  # noqa: E501
        )  # noqa: E501
      finally:
        # Release lock using helper
        _ = release_lock(cache_key, token)
    case Err(e):
      # Could not acquire lock, continue to polling
      print(
        f"\n[DEBUG-REDIS-CACHING] Could not acquire lock so switch to polling: {e}\n"  # noqa: E501
      )  # noqa: E501
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
          payload = filter_payload_by_radius(
            payload, latitude, longitude, radius
          )
        return Ok(payload)
      case Err(e):
        print(f"\n[DEBUG-REDIS-CACHING] Polling cache miss: {e}\n")
        continue

  # Might not need this but I put it just in case as our ultimate fallback,
  # We call the caller ourselves
  try:
    center_lat, center_lon = s2cell.token_to_lat_lon(cache_key)
    payload = caller(center_lat, center_lon, radius)
    # Cache the fallback result
    cache_result = set_json(cache_key, payload, expire_seconds=cache_ttl)
    match cache_result:
      case Ok(_):
        print(
          f"\n[DEBUG-REDIS-CACHING] WARNING: cached via fallback data for key: {cache_key}\n"  # noqa: E501
        )
        # before we return the payload, we filter it by the radius
        if filter_by_distance:
          payload = filter_payload_by_radius(
            payload, latitude, longitude, radius
          )
        return Ok(payload)
      case Err(e):
        return Err(f"Failed to cache fallback data: {e}")
  except Exception as e:
    return Err(f"Fallback fetch failed: {e}")


def filter_payload_by_radius(
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
      print(f"[DEBUG-REDIS-CACHING] Haversine distance: {haversine_distance}")
      if haversine_distance <= radius_m:
        filtered.append(place)
    except Exception:
      # if any parsing fails, keep the place (fail-open)
      filtered.append(place)
  return {"places": filtered}
