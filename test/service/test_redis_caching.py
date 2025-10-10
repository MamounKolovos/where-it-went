import math
from typing import Any
from unittest.mock import MagicMock, Mock, patch

from where_it_went.service.redis_caching import (
  build_region_key_s2,
  fetch_or_cache_region,
  filter_payload_by_radius,
  haversine_distance_m,
)
from where_it_went.utils.result import Err, Ok


def haversine_distance_same_point_test():
  """Test distance between same point is zero."""
  lat, lon = 38.83, -77.31
  distance = haversine_distance_m(lat, lon, lat, lon)
  assert distance == 0.0


def haversine_distance_known_distance_test():
  """Test distance between known points."""
  # Distance between Washington DC and New York City
  dc_lat, dc_lon = 38.9072, -77.0369
  ny_lat, ny_lon = 40.7128, -74.0060
  distance = haversine_distance_m(dc_lat, dc_lon, ny_lat, ny_lon)
  # Should be approximately 330km
  assert 320000 < distance < 340000  # Within reasonable range


def haversine_distance_opposite_side_of_earth_test():
  """Test distance calculation across the globe."""
  # Point and its antipode (opposite side of Earth)
  lat1, lon1 = 0.0, 0.0
  lat2, lon2 = 0.0, 180.0
  distance = haversine_distance_m(lat1, lon1, lat2, lon2)
  # Should be approximately half the Earth's circumference
  expected = math.pi * 6371000  # Earth's radius * π
  assert abs(distance - expected) < 1000  # Within 1km tolerance


def build_region_key_s2_consistent_test():
  """Test that same coordinates generate consistent keys."""
  lat, lon, radius = 38.83, -77.31, 5000.0
  key1 = build_region_key_s2(lat, lon, radius)
  key2 = build_region_key_s2(lat, lon, radius)
  assert key1 == key2


def build_region_key_s2_different_coords_test():
  """Test that different coordinates generate different keys."""
  key1 = build_region_key_s2(38.83, -77.31, 5000.0)
  key2 = build_region_key_s2(39.83, -78.31, 5000.0)  # Much further apart
  assert key1 != key2


def build_region_key_s2_custom_level_test():
  """Test custom S2 level parameter."""
  lat, lon, radius = 38.83, -77.31, 5000.0
  key1 = build_region_key_s2(lat, lon, radius, s2_level=15)
  key2 = build_region_key_s2(lat, lon, radius, s2_level=16)
  assert key1 != key2


def filter_payload_by_radius_empty_payload_test():
  """Test filtering empty payload."""
  payload: dict[Any, Any] = {}
  result = filter_payload_by_radius(payload, 38.83, -77.31, 5000.0)
  assert result == payload


def filter_payload_by_radius_no_places_key_test():
  """Test payload without places key."""
  payload = {"other": "data"}
  result = filter_payload_by_radius(payload, 38.83, -77.31, 5000.0)
  assert result == payload


def filter_payload_by_radius_all_within_radius_test():
  """Test filtering when all places are within radius."""
  center_lat, center_lon = 38.83, -77.31
  radius = 5000.0

  places = [
    {"latitude": 38.84, "longitude": -77.30, "name": "place1"},
    {"latitude": 38.82, "longitude": -77.32, "name": "place2"},
  ]
  payload = {"places": places}

  result = filter_payload_by_radius(payload, center_lat, center_lon, radius)
  assert len(result["places"]) == 2


def filter_payload_by_radius_some_outside_radius_test():
  """Test filtering when some places are outside radius."""
  center_lat, center_lon = 38.83, -77.31
  radius = 1000.0  # Small radius

  places = [
    {
      "latitude": 38.831,
      "longitude": -77.311,
      "name": "close_place",
    },  # Very close, within 1km
    {
      "latitude": 38.90,
      "longitude": -77.20,
      "name": "far_place",
    },  # Far away, outside 1km
  ]
  payload = {"places": places}

  result = filter_payload_by_radius(payload, center_lat, center_lon, radius)
  assert len(result["places"]) == 1
  assert result["places"][0]["name"] == "close_place"


def filter_payload_by_radius_invalid_coordinates_test():
  """Test filtering with invalid coordinates (fail-open behavior)."""
  center_lat, center_lon = 38.83, -77.31
  radius = 1000.0

  places = [
    {"latitude": "invalid", "longitude": -77.30, "name": "invalid_place"},
    {
      "latitude": 38.831,
      "longitude": -77.311,
      "name": "valid_place",
    },  # Very close
  ]
  payload = {"places": places}

  result = filter_payload_by_radius(payload, center_lat, center_lon, radius)
  # Should keep both places (fail-open)
  assert len(result["places"]) == 2


@patch("where_it_went.service.redis_caching.get_json")
def cache_hit_test(
  mock_get_json: MagicMock,
):
  """Test cache hit scenario."""
  # Mock cache hit
  cached_data = {
    "places": [{"latitude": 38.84, "longitude": -77.30, "name": "test"}]
  }
  mock_get_json.return_value = Ok(cached_data)

  mock_caller = Mock(return_value={"places": []})  # Should not be called

  result = fetch_or_cache_region(
    latitude=38.83, longitude=-77.31, radius=5000.0, caller=mock_caller
  )

  match result:
    case Ok(data):
      assert data == cached_data
    case _:
      assert False, "Expected a cached result"
  mock_get_json.assert_called_once()
  mock_caller.assert_not_called()


@patch("where_it_went.service.redis_caching.release_lock")
@patch("where_it_went.service.redis_caching.acquire_lock")
@patch("where_it_went.service.redis_caching.set_json")
@patch("where_it_went.service.redis_caching.get_json")
def cache_miss_and_populate_test(
  mock_get_json: MagicMock,
  mock_set_json: MagicMock,
  mock_acquire_lock: MagicMock,
  mock_release_lock: MagicMock,
):
  """Test cache miss and population scenario."""
  # Mock cache miss then successful lock acquisition
  mock_get_json.return_value = Err("Key not found")
  mock_acquire_lock.return_value = Ok("lock_token")
  mock_set_json.return_value = Ok(True)
  mock_release_lock.return_value = Ok(True)

  api_data = {
    "places": [{"latitude": 38.84, "longitude": -77.30, "name": "test"}]
  }
  mock_caller = Mock(return_value=api_data)

  result = fetch_or_cache_region(
    latitude=38.83, longitude=-77.31, radius=5000.0, caller=mock_caller
  )

  match result:
    case Ok(data):
      assert data == api_data
    case _:
      assert False, "Expected a populated result"
  mock_caller.assert_called_once()
  mock_set_json.assert_called_once()
  # Get the actual token value from the Ok result
  match mock_acquire_lock.return_value:
    case Ok(token):
      mock_release_lock.assert_called_once_with("89b64f", token)
    case _:
      assert False, "Expected Ok result"


@patch("where_it_went.service.redis_caching.set_json")
@patch("where_it_went.service.redis_caching.acquire_lock")
@patch("where_it_went.service.redis_caching.get_json")
def lock_acquisition_failure_test(
  mock_get_json: MagicMock,
  mock_acquire_lock: MagicMock,
  mock_set_json: MagicMock,
):
  """Test when lock acquisition fails."""
  # Mock cache miss and lock failure, but successful fallback caching
  mock_get_json.return_value = Err("Key not found")
  mock_acquire_lock.return_value = Err("Lock acquisition failed")
  mock_set_json.return_value = Ok(True)

  mock_caller = Mock(return_value={"places": []})

  result = fetch_or_cache_region(
    latitude=38.83, longitude=-77.31, radius=5000.0, caller=mock_caller
  )

  # Should fallback to direct call
  match result:
    case Ok(_):
      pass
    case _:
      assert False, "Expected a populated result"
  mock_caller.assert_called_once()


@patch("where_it_went.service.redis_caching.release_lock")
@patch("where_it_went.service.redis_caching.acquire_lock")
@patch("where_it_went.service.redis_caching.set_json")
@patch("where_it_went.service.redis_caching.get_json")
def cache_set_failure_test(
  mock_get_json: MagicMock,
  mock_set_json: MagicMock,
  mock_acquire_lock: MagicMock,
  mock_release_lock: MagicMock,
):
  """Test when cache set operation fails."""
  # Mock cache miss, successful lock, but cache set failure
  mock_get_json.return_value = Err("Key not found")
  mock_acquire_lock.return_value = Ok("lock_token")
  mock_set_json.return_value = Err("Redis connection failed")
  mock_release_lock.return_value = Ok(True)

  api_data = {
    "places": [{"latitude": 38.84, "longitude": -77.30, "name": "test"}]
  }
  mock_caller = Mock(return_value=api_data)

  result = fetch_or_cache_region(
    latitude=38.83, longitude=-77.31, radius=5000.0, caller=mock_caller
  )

  match result:
    case Err(error):
      assert "Failed to cache data" in error
    case _:
      assert False, "Expected a failed result"


@patch("where_it_went.service.redis_caching.acquire_lock")
@patch("where_it_went.service.redis_caching.get_json")
def caller_exception_test(
  mock_get_json: MagicMock,
  mock_acquire_lock: MagicMock,
):
  """Test when caller function raises an exception."""
  # Mock cache miss and successful lock
  mock_get_json.return_value = Err("Key not found")
  mock_acquire_lock.return_value = Ok("lock_token")

  mock_caller = Mock(side_effect=Exception("API call failed"))

  result = fetch_or_cache_region(
    latitude=38.83, longitude=-77.31, radius=5000.0, caller=mock_caller
  )

  match result:
    case Err(error):
      assert "Failed to fetch data" in error
    case _:
      assert False, "Expected a failed result"


@patch("where_it_went.service.redis_caching.set_json")
@patch("where_it_went.service.redis_caching.get_json")
def edge_case_zero_radius_test(
  mock_get_json: MagicMock, mock_set_json: MagicMock
):
  """Test edge case with zero radius."""
  # Mock cache miss and successful operations
  mock_get_json.return_value = Err("Key not found")
  mock_set_json.return_value = Ok(True)

  mock_caller = Mock(return_value={"places": []})

  result = fetch_or_cache_region(
    latitude=38.83, longitude=-77.31, radius=0.0, caller=mock_caller
  )

  # Should handle zero radius gracefully
  match result:
    case Ok(_):
      pass
    case _:
      assert False, "Expected a populated result"


@patch("where_it_went.service.redis_caching.set_json")
@patch("where_it_went.service.redis_caching.get_json")
def edge_case_negative_radius_test(
  mock_get_json: MagicMock, mock_set_json: MagicMock
):
  """Test edge case with negative radius."""
  # Mock cache miss and successful operations
  mock_get_json.return_value = Err("Key not found")
  mock_set_json.return_value = Ok(True)

  mock_caller = Mock(return_value={"places": []})

  result = fetch_or_cache_region(
    latitude=38.83, longitude=-77.31, radius=-100.0, caller=mock_caller
  )

  # Should handle negative radius gracefully
  match result:
    case Ok(_):
      pass
    case _:
      assert False, "Expected a populated result"


@patch("where_it_went.service.redis_caching.acquire_lock")
@patch("where_it_went.service.redis_caching.get_json")
def polling_behavior_test(
  mock_get_json: MagicMock,
  mock_acquire_lock: MagicMock,
):
  """Test polling behavior when lock cannot be acquired."""
  # Mock cache miss, lock failure, then cache hit during polling
  mock_get_json.side_effect = [
    Err("Key not found"),  # Initial cache miss
    Ok(
      {"places": [{"latitude": 38.84, "longitude": -77.30, "name": "test"}]}
    ),  # Polling cache hit
  ]
  mock_acquire_lock.return_value = Err("Lock acquisition failed")

  mock_caller = Mock(return_value={"places": []})

  result = fetch_or_cache_region(
    latitude=38.83,
    longitude=-77.31,
    radius=5000.0,
    caller=mock_caller,
    wait_timeout=0.1,  # Short timeout for testing
    poll_interval=0.01,
  )

  match result:
    case Ok(_):
      pass
    case _:
      assert False, "Expected a populated result"
  assert mock_get_json.call_count >= 2  # Should have polled
  mock_caller.assert_not_called()  # Should not have called API
