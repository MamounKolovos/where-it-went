from dataclasses import dataclass

from pydantic import BaseModel, TypeAdapter, ValidationError
from redis import Redis

from where_it_went.service.search_places import api, s2helpers
from where_it_went.utils import listutils, pipe, result
from where_it_went.utils.result import Err, Ok, Result


class Place(BaseModel):
  name: str
  latitude: float
  longitude: float
  state: str
  zip_code: str
  types: list[str]


@result.with_unwrap
def decode_place(api_place: api.ApiPlace) -> Result[Place, str]:
  state = pipe(
    api_place.address_components,
    listutils.find(
      lambda component: "administrative_area_level_1" in component.types
    ),
    result.replace_error(
      f"Api could not find the state that {api_place.display_name.name} is in"
    ),
    result.unwrap(),
    lambda component: component.long_text,
  )

  zip_code = pipe(
    api_place.address_components,
    listutils.find(lambda component: "postal_code" in component.types),
    result.replace_error(
      f"Api could not find the zip code that {api_place.display_name.name} is in"  # noqa: E501
    ),
    result.unwrap(),
    lambda component: component.long_text,
  )

  return Ok(
    Place(
      name=api_place.display_name.name,
      latitude=api_place.location.latitude,
      longitude=api_place.location.longitude,
      state=state,
      zip_code=zip_code,
      types=api_place.types,
    )
  )


# TODO: sender callback instead of hardcoding send_request
@result.with_unwrap
def fetch_places_for_cell(
  cell: s2helpers.Cell,
) -> Result[list[Place], str]:
  radius = s2helpers.LEVEL_TO_DIAMETER[cell.level] / 2

  api_request_model = api.build_api_request(
    cell.latitude, cell.longitude, radius
  )

  api_response = pipe(api.send_request(api_request_model), result.unwrap())

  api_response_model = pipe(api_response, api.handle_response, result.unwrap())

  places = pipe(
    listutils.try_map(decode_place, api_response_model.places), result.unwrap()
  )

  return Ok(places)


DEFAULT_CACHE_TTL = 60 * 60 * 12  # 12 hours


@dataclass(frozen=True)
class CacheMiss: ...


@dataclass(frozen=True)
class CorruptedValue: ...


type CacheError = CacheMiss | CorruptedValue

PLACES_ADAPTER = TypeAdapter(list[Place])


def serialize_places(places: list[Place]) -> bytes:
  return PLACES_ADAPTER.dump_json(places)


def deserialize_places(b: bytes) -> Result[list[Place], str]:
  try:
    return Ok(PLACES_ADAPTER.validate_json(b, by_alias=True))
  except ValidationError as e:
    return Err(str(e))


def load_places_from_cache(
  client: Redis, cell: s2helpers.Cell
) -> Result[list[Place], CacheError]:
  match client.get(cell.token):
    case None:
      return Err(CacheMiss())
    case bytes(value):
      return result.replace_error(CorruptedValue(), deserialize_places(value))
    case _:
      raise RuntimeError("Only raw bytes should be stored in the cache")


def cache_places(
  client: Redis, cell: s2helpers.Cell, places: list[Place]
) -> None:
  _ = client.set(cell.token, serialize_places(places), ex=DEFAULT_CACHE_TTL)


MAX_RECURSION_LEVEL = 16


def calc_dist_from_region_to_nearest_boundary(
  region: s2helpers.SearchRegion, parent: s2helpers.Cell
) -> float:
  parent_bounds = s2helpers.get_bounds(parent)
  dist_from_point_to_top_edge = s2helpers.haversine_distance(
    region.latitude,
    region.longitude,
    parent_bounds.latitude_max,
    region.longitude,
  )
  dist_from_point_to_bottom_edge = s2helpers.haversine_distance(
    region.latitude,
    region.longitude,
    parent_bounds.latitude_min,
    region.longitude,
  )
  dist_from_point_to_left_edge = s2helpers.haversine_distance(
    region.latitude,
    region.longitude,
    region.latitude,
    parent_bounds.longitude_min,
  )
  dist_from_point_to_right_edge = s2helpers.haversine_distance(
    region.latitude,
    region.longitude,
    region.latitude,
    parent_bounds.longitude_max,
  )
  print(
    f"[DEBUG] Dist from point to top edge: {dist_from_point_to_top_edge}m"  # noqa: E501
  )
  print(
    f"[DEBUG] Dist from point to bottom edge: {dist_from_point_to_bottom_edge}m"  # noqa: E501
  )
  print(
    f"[DEBUG] Dist from point to left edge: {dist_from_point_to_left_edge}m"  # noqa: E501
  )
  print(
    f"[DEBUG] Dist from point to right edge: {dist_from_point_to_right_edge}m"  # noqa: E501
  )
  dist_from_point_to_nearest_boundary = min(
    dist_from_point_to_top_edge,
    dist_from_point_to_bottom_edge,
    dist_from_point_to_left_edge,
    dist_from_point_to_right_edge,
  )
  return dist_from_point_to_nearest_boundary


def get_places_in_region(
  client: Redis, region: s2helpers.SearchRegion
) -> list[Place]:
  print(
    f"\n[DEBUG] === Getting places for region at ({region.latitude:.6f}, {region.longitude:.6f}) with radius {region.radius}m ==="  # noqa: E501
  )
  cell = s2helpers.search_region_to_cell(region)
  print(f"[DEBUG] Region cell: {cell.token} (level {cell.level})")
  parent = s2helpers.get_parent(cell)
  print(f"[DEBUG] Parent cell: {parent.token} (level {parent.level})")
  # including parent cell only when the region is within the cell
  neighbors = [cell]
  places_included: list[Place] = []
  dist_from_point_to_cell_boundary = calc_dist_from_region_to_nearest_boundary(
    region, parent
  )
  print(
    f"[DEBUG] Distance to nearest boundary: {dist_from_point_to_cell_boundary:.2f}m"  # noqa: E501
  )
  if dist_from_point_to_cell_boundary <= region.radius:
    neighbors.extend(s2helpers.get_intersecting_cells(region, cell))

    print(
      f"[DEBUG] Region extends beyond cell boundary - checking {len(neighbors)} cells"  # noqa: E501
    )
  else:
    print("[DEBUG] Region stays within parent cell - checking 1 cell")

  for neighbor in neighbors if neighbors else [parent]:
    places = get_places_in_region_loop(client, region, neighbor)
    cache_places(client, neighbor, places)
    places_included.extend(places)

  filtered_places = listutils.filter(
    lambda place: s2helpers.haversine_distance(
      region.latitude, region.longitude, place.latitude, place.longitude
    )
    <= region.radius,
    places_included,
  )
  print(
    f"[DEBUG] Total places found: {len(filtered_places)} (from {len(places_included)} before filtering)"  # noqa: E501
  )
  return filtered_places


def get_places_in_region_loop(
  client: Redis, region: s2helpers.SearchRegion, cell: s2helpers.Cell
) -> list[Place]:
  match cell.level:
    case level if level >= MAX_RECURSION_LEVEL:
      places = pipe(
        cell,
        fetch_places_for_cell,
        result.unwrap_or([]),
      )
      return places
    case level:
      places: list[Place] = []

      for child in s2helpers.get_children(cell):
        match load_places_from_cache(client, child):
          case Ok(child_places):
            places.extend(child_places)
          case Err(CacheMiss()):
            child_places = get_places_in_region_loop(client, region, child)
            cache_places(client, child, child_places)
            places.extend(child_places)
          case Err(CorruptedValue()):
            print("[DEBUG] Value corrupted")
            pass
          case _:
            pass

      return places
