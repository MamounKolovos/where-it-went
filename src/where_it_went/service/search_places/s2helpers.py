import math
from dataclasses import dataclass

import s2cell  # pyright: ignore[reportMissingTypeStubs]

from where_it_went.utils import listutils, pipe

MAX_S2_LEVEL = 24
MIN_S2_LEVEL = 10

LEVEL_TO_DIAMETER: dict[int, float] = {
  10: 9766.0,
  11: 4883.0,
  12: 2441.0,
  13: 1220.0,
  14: 610.0,
  15: 305.0,
  16: 153.0,
  17: 76.0,
  18: 38.0,
  19: 19.0,
  20: 9.5,
  21: 4.8,
  22: 2.4,
  23: 1.2,
  24: 0.6,
}


def radius_to_level(radius: float) -> int:
  diameter = radius * 2

  left_index = MIN_S2_LEVEL
  right_index = MAX_S2_LEVEL

  while left_index < right_index:
    middle_index = (left_index + right_index + 1) // 2
    if LEVEL_TO_DIAMETER[middle_index] >= diameter:
      left_index = middle_index
    else:
      right_index = middle_index - 1

  return left_index


@dataclass(frozen=True)
class SearchRegion:
  """
  Circular region that represents the user's field of view
  """

  latitude: float
  longitude: float
  radius: float


@dataclass(frozen=True)
class Cell:
  """
  Wrapper type for S2Cell
  """

  id: int
  token: str
  level: int
  latitude: float
  longitude: float


def clamp[a: float | int](value: a, minimum: a, maximum: a) -> a:
  match value:
    case value if value < minimum:
      return minimum
    case value if value > maximum:
      return maximum
    case value:
      return value


def new_search_region(
  latitude: float, longitude: float, radius: float
) -> SearchRegion:
  return SearchRegion(
    latitude=clamp(latitude, -90.0, 90.0),
    longitude=clamp(longitude, -180.0, 180),
    radius=clamp(radius, 0.0, 1000.0),
  )


def search_region_to_cell(region: SearchRegion) -> Cell:
  level = radius_to_level(region.radius)
  id = s2cell.lat_lon_to_cell_id(region.latitude, region.longitude, level=level)
  token = s2cell.cell_id_to_token(id)
  return Cell(
    id=id,
    token=token,
    level=level,
    latitude=region.latitude,
    longitude=region.longitude,
  )


@dataclass(frozen=True)
class CellBounds:
  latitude_min: float
  longitude_min: float
  latitude_max: float
  longitude_max: float


def get_bounds(cell: Cell) -> CellBounds:
  half_size = LEVEL_TO_DIAMETER[cell.level] / 2
  # 111320 is meters per degree for latitude
  delta_latitude = half_size / 111320
  delta_longitude = half_size / (111320 * math.cos(math.radians(cell.latitude)))

  latitude_min = cell.latitude - delta_latitude
  longitude_min = cell.longitude - delta_longitude
  latitude_max = cell.latitude + delta_latitude
  longitude_max = cell.longitude + delta_longitude

  return CellBounds(
    latitude_min=latitude_min,
    longitude_min=longitude_min,
    latitude_max=latitude_max,
    longitude_max=longitude_max,
  )


def _lowest_one_bit_mask(cell_id: int) -> int:
  return cell_id & (~cell_id + 1)


def get_parent(cell: Cell) -> Cell:
  parent_id = s2cell.cell_id_to_parent_cell_id(cell.id)
  parent_token = s2cell.cell_id_to_token(parent_id)
  parent_level = s2cell.cell_id_to_level(parent_id)
  parent_latitude, parent_longitude = s2cell.cell_id_to_lat_lon(parent_id)
  return Cell(
    parent_id, parent_token, parent_level, parent_latitude, parent_longitude
  )


def get_children(cell: Cell) -> list[Cell]:
  children: list[Cell] = []

  new_lobm = _lowest_one_bit_mask(cell.id) >> 2
  for position in range(4):
    id = cell.id + (2 * position + 1 - 4) * new_lobm
    token = s2cell.cell_id_to_token(id)
    latitude, longitude = s2cell.cell_id_to_lat_lon(id)
    level = s2cell.cell_id_to_level(id)

    child = Cell(
      id=id, token=token, level=level, latitude=latitude, longitude=longitude
    )
    children.append(child)
  return children


def get_neighbors(cell: Cell) -> list[Cell]:
  neighbors: list[Cell] = []

  for neighbor_id in s2cell.cell_id_to_neighbor_cell_ids(
    cell.id, edge=True, corner=True
  ):
    token = s2cell.cell_id_to_token(neighbor_id)
    latitude, longitude = s2cell.cell_id_to_lat_lon(neighbor_id)
    level = s2cell.cell_id_to_level(neighbor_id)

    neighbor = Cell(
      id=neighbor_id,
      token=token,
      level=level,
      latitude=latitude,
      longitude=longitude,
    )
    neighbors.append(neighbor)
  return neighbors


def haversine_distance(
  latitude1: float, longitude1: float, latitude2: float, longitude2: float
) -> float:
  """Return distance in meters between two lat/lon points"""
  earth_radius_in_meters = 6371000.0
  phi1, phi2 = math.radians(latitude1), math.radians(latitude2)
  delta_latitude = phi2 - phi1
  delta_longitude = math.radians(longitude2 - longitude1)
  haversine_of_central_angle = (
    math.sin(delta_latitude / 2) ** 2
    + math.cos(phi1) * math.cos(phi2) * math.sin(delta_longitude / 2) ** 2
  )
  return (
    # converting angular distance to linear distance
    earth_radius_in_meters
    * 2
    * math.asin(math.sqrt(haversine_of_central_angle))
  )


def search_region_intersects_cell(region: SearchRegion, cell: Cell) -> bool:
  bounds = get_bounds(cell)

  closest_latitude = clamp(
    region.latitude, bounds.latitude_min, bounds.latitude_max
  )
  closest_longitude = clamp(
    region.longitude, bounds.longitude_min, bounds.longitude_max
  )

  distance = haversine_distance(
    region.latitude, region.longitude, closest_latitude, closest_longitude
  )
  return distance <= region.radius


def get_intersecting_cells(
  region: SearchRegion, center_cell: Cell
) -> list[Cell]:
  intersecting_neighbors = pipe(
    center_cell,
    get_neighbors,
    listutils.filter(
      lambda neighbor: search_region_intersects_cell(region, neighbor)
    ),
  )

  return [center_cell, *intersecting_neighbors]
