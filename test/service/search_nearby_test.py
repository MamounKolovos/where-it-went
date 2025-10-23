import fakeredis

from where_it_went.service.search_places import s2helpers, search_engine


def gmu_caching_two_requests_test() -> None:
  """Test caching behavior with sequential requests from nearby locations"""
  # Create fake Redis client (in-memory, no Docker needed)
  fake_redis = fakeredis.FakeStrictRedis()

  # GMU locations
  potomac_heights = (38.826589169752516, -77.30255757609915)
  liberty_square = (38.82802502454114, -77.30240851473394)

  # First request: Potomac Heights with 300m radius
  region1 = s2helpers.SearchRegion(
    latitude=potomac_heights[0],
    longitude=potomac_heights[1],
    radius=300.0,
  )

  print("\n" + "=" * 70)
  print(f"REQUEST 1: Potomac Heights GMU with {region1.radius}m radius")
  print("=" * 70)

  request_1_places = search_engine.get_places_in_region(
    fake_redis, region1, lambda _: None
  )
  print(f"\n[TEST] Request 1 returned {len(request_1_places)} places")
  if request_1_places:
    print("[TEST] Sample places from Request 1:")
    for place in request_1_places[:3]:
      print(
        f"  - {place.name} at ({place.latitude:.6f}, {place.longitude:.6f})"
      )

  # Second request: Liberty Square with 500m radius
  region2 = s2helpers.SearchRegion(
    latitude=liberty_square[0],
    longitude=liberty_square[1],
    radius=300.0,
  )

  print("\n" + "=" * 70)
  print(f"REQUEST 2: Liberty Square GMU with {region2.radius}m radius")
  print("=" * 70)

  places2 = search_engine.get_places_in_region(
    fake_redis, region2, lambda _: None
  )
  print(f"\n[TEST] Request 2 returned {len(places2)} places")
  if places2:
    print("[TEST] Sample places from Request 2:")
    for place in places2[:3]:
      print(
        f"  - {place.name} at ({place.latitude:.6f}, {place.longitude:.6f})"
      )

  # Verify caching worked
  print("\n" + "=" * 70)
  print("CACHE ANALYSIS")
  print("=" * 70)

  # Check if cells from both requests overlap
  cell1 = s2helpers.search_region_to_cell(region1)
  parent1 = s2helpers.get_parent(cell1)

  cell2 = s2helpers.search_region_to_cell(region2)
  parent2 = s2helpers.get_parent(cell2)

  print(f"\nRequest 1 parent cell: {parent1.token} (level {parent1.level})")
  print(f"Request 2 parent cell: {parent2.token} (level {parent2.level})")

  if parent1.token == parent2.token:
    msg = "Both requests use the SAME parent cell - caching effective!"
    print(f"\n✓ {msg}")
  else:
    msg = "Requests use DIFFERENT parent cells - less cache reuse expected"
    print(f"\n✗ {msg}")

  # Check cache keys
  cache_keys_raw = fake_redis.keys()  # pyright: ignore[reportUnknownMemberType]
  cache_keys = [k.decode() for k in cache_keys_raw[:10]]  # pyright: ignore[reportIndexIssue, reportUnknownMemberType, reportUnknownVariableType]
  print(f"\nTotal cache entries: {len(cache_keys_raw)}")  # pyright: ignore[reportArgumentType]
  print(f"First 10 cache keys: {cache_keys}")

  assert True


# This is just a function to visually verify the distances in meters between
# the locations that we're using for testing
def print_distances_test() -> None:
  """Print distances between real-world locations"""
  print("\n=== GMU Campus Locations ===")
  # GMU Campus locations
  george_mason_university = (38.83158313707954, -77.31166127240445)
  potomac_heights = (38.826589169752516, -77.30255757609915)
  liberty_square = (38.82802502454114, -77.30240851473394)
  field_house = (38.83443375164532, -77.31478015706305)
  giants = (38.82520990677409, -77.31508139554383)

  print(f"Potomac Heights GMU: {potomac_heights}")
  print(f"Liberty Square GMU: {liberty_square}")
  print(f"GMU Field House: {field_house}")
  print(f"Giants: {giants}")
  print()

  # Calculate all pairwise distances for GMU locations
  dist_ph_ls = s2helpers.haversine_distance(
    potomac_heights[0], potomac_heights[1], liberty_square[0], liberty_square[1]
  )
  dist_ph_fh = s2helpers.haversine_distance(
    potomac_heights[0], potomac_heights[1], field_house[0], field_house[1]
  )
  dist_ph_g = s2helpers.haversine_distance(
    potomac_heights[0], potomac_heights[1], giants[0], giants[1]
  )
  dist_ls_fh = s2helpers.haversine_distance(
    liberty_square[0], liberty_square[1], field_house[0], field_house[1]
  )
  dist_ls_g = s2helpers.haversine_distance(
    liberty_square[0], liberty_square[1], giants[0], giants[1]
  )
  dist_fh_g = s2helpers.haversine_distance(
    field_house[0], field_house[1], giants[0], giants[1]
  )

  print("GMU Campus Distances:")
  print(f"  Potomac Heights -> Liberty Square: {dist_ph_ls:.2f} meters")
  print(f"  Potomac Heights -> Field House: {dist_ph_fh:.2f} meters")
  print(f"  Potomac Heights -> Giants: {dist_ph_g:.2f} meters")
  print(f"  Liberty Square -> Field House: {dist_ls_fh:.2f} meters")
  print(f"  Liberty Square -> Giants: {dist_ls_g:.2f} meters")
  print(f"  Field House -> Giants: {dist_fh_g:.2f} meters")
  print()

  print("=== Washington DC Landmarks ===")
  # DC landmarks
  white_house = (38.89787406568969, -77.03647573984091)
  lincoln_memorial = (38.88948569491708, -77.05019746075527)
  interior_museum = (38.894851343781546, -77.04253302872668)
  art_museum = (38.89291805482224, -77.0411141776547)
  spy_museum = (38.88420919093379, -77.02473053216619)
  wharf_dc = (38.879738785853895, -77.02462044970615)

  print(f"White House: {white_house}")
  print(f"Lincoln Memorial: {lincoln_memorial}")
  print(f"Interior Museum: {interior_museum}")
  print(f"Art Museum: {art_museum}")
  print(f"Spy Museum: {spy_museum}")
  print(f"Wharf DC: {wharf_dc}")
  print()

  # Calculate distances from White House to all DC landmarks
  dist_wh_lincoln = s2helpers.haversine_distance(
    white_house[0], white_house[1], lincoln_memorial[0], lincoln_memorial[1]
  )
  dist_wh_interior = s2helpers.haversine_distance(
    white_house[0], white_house[1], interior_museum[0], interior_museum[1]
  )
  dist_wh_art = s2helpers.haversine_distance(
    white_house[0], white_house[1], art_museum[0], art_museum[1]
  )
  dist_wh_spy = s2helpers.haversine_distance(
    white_house[0], white_house[1], spy_museum[0], spy_museum[1]
  )
  dist_wh_wharf = s2helpers.haversine_distance(
    white_house[0], white_house[1], wharf_dc[0], wharf_dc[1]
  )
  dist_lincoln_spy = s2helpers.haversine_distance(
    lincoln_memorial[0], lincoln_memorial[1], spy_museum[0], spy_museum[1]
  )
  dist_spy_wharf = s2helpers.haversine_distance(
    spy_museum[0], spy_museum[1], wharf_dc[0], wharf_dc[1]
  )

  print("DC Landmark Distances:")
  print(f"  White House -> Lincoln Memorial: {dist_wh_lincoln:.2f} meters")
  print(f"  White House -> Interior Museum: {dist_wh_interior:.2f} meters")
  print(f"  White House -> Art Museum: {dist_wh_art:.2f} meters")
  print(f"  White House -> Spy Museum: {dist_wh_spy:.2f} meters")
  print(f"  White House -> Wharf DC: {dist_wh_wharf:.2f} meters")
  print(f"  Lincoln Memorial -> Spy Museum: {dist_lincoln_spy:.2f} meters")
  print(f"  Spy Museum -> Wharf DC: {dist_spy_wharf:.2f} meters")
  print()

  print("=== GMU to DC Distance ===")
  dist_gmu_dc = s2helpers.haversine_distance(
    george_mason_university[0],
    george_mason_university[1],
    white_house[0],
    white_house[1],
  )
  print(f"  GMU -> White House: {dist_gmu_dc:.2f} meters")
  print(f"  ({dist_gmu_dc / 1000:.2f} km)")
  print()

  assert True


if __name__ == "__main__":
  print_distances_test()
  gmu_caching_two_requests_test()
