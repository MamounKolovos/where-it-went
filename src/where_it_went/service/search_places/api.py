from http import HTTPStatus
from typing import Any

import requests
from pydantic import BaseModel, Field

from where_it_went import config
from where_it_went.utils import pipe, result
from where_it_went.utils.decoding import decode_model
from where_it_went.utils.http import parse_response_json
from where_it_went.utils.result import Ok, Result

API_URL = "https://places.googleapis.com/v1"
SEARCH_NEARBY_ENDPOINT = "/places:searchNearby"

# Exclude types NOT relevant for federal spending
EXCLUDED_PLACE_TYPES = [
  # Automotive
  "car_dealer",
  "car_rental",
  "car_repair",
  "car_wash",
  "electric_vehicle_charging_station",
  "gas_station",
  "parking",
  "rest_stop",
  # Food and Drink (all restaurants/bars/cafes)
  "restaurant",
  "bar",
  "cafe",
  "bakery",
  "fast_food_restaurant",
  "coffee_shop",
  # Lodging
  "hotel",
  "motel",
  "lodging",
  # Shopping (retail stores)
  "clothing_store",
  "shoe_store",
  "store",
  "supermarket",
  "grocery_store",
  "shopping_mall",
  # Sports/Recreation
  "gym",
  "fitness_center",
  "sports_club",
  # Personal Services
  "barber_shop",
  "beauty_salon",
  "hair_salon",
  "nail_salon",
  "spa",
  "laundry",
  # Places of Worship
  "church",
  "mosque",
  "synagogue",
  "hindu_temple",
]

places_session = requests.Session()
places_session.headers.update(
  {
    "Content-Type": "application/json",
    "X-Goog-FieldMask": str.join(
      ",",
      [
        "places.displayName",
        "places.location",
        "places.types",
        "places.formattedAddress",
        "places.addressComponents",
      ],
    ),
  }
)


class SearchNearbyRequest(BaseModel):
  latitude: float
  longitude: float
  radius: float  # meters


class Center(BaseModel):
  latitude: float
  longitude: float


class Circle(BaseModel):
  center: Center
  radius: float


class LocationRestriction(BaseModel):
  circle: Circle


class NearbySearchPlacesApiRequest(BaseModel):
  location_restriction: LocationRestriction = Field(
    ..., alias="locationRestriction"
  )
  max_result_count: int = Field(..., alias="maxResultCount")
  included_types: list[str] = Field(default_factory=list, alias="includedTypes")
  excluded_types: list[str] = Field(default_factory=list, alias="excludedTypes")


class DisplayName(BaseModel):
  language_code: str | None = Field(None, alias="languageCode")
  name: str = Field(..., alias="text")


class Location(BaseModel):
  latitude: float
  longitude: float


class AddressComponent(BaseModel):
  long_text: str = Field(..., alias="longText")
  short_text: str | None = Field(None, alias="shortText")
  types: list[str] = Field(default_factory=list)


class ApiPlace(BaseModel):
  display_name: DisplayName = Field(..., alias="displayName")
  location: Location
  types: list[str]
  formatted_address: str = Field(..., alias="formattedAddress")
  address_components: list[AddressComponent] = Field(
    ..., alias="addressComponents"
  )


class NearbySearchPlacesApiResponse(BaseModel):
  # default to empty list necessary for consistent response structure
  # if there are no nearby places, the endpoint will return {} not {places: []}
  places: list[ApiPlace] = []


def build_api_request(
  latitude: float, longitude: float, radius: float
) -> NearbySearchPlacesApiRequest:
  # define like this instead of calling models directly for readability
  # nested model calls are hard to read
  request_dict: dict[str, Any] = {
    "locationRestriction": {
      "circle": {
        "center": {
          "latitude": latitude,
          "longitude": longitude,
        },
        "radius": radius,
      }
    },
    "maxResultCount": 20,
    "excludedTypes": EXCLUDED_PLACE_TYPES,
  }
  return NearbySearchPlacesApiRequest(**request_dict)


@result.with_unwrap
def send_request(
  api_request_model: NearbySearchPlacesApiRequest,
) -> Result[dict[str, Any], str]:
  places_api_key = pipe(
    config.get_places_api_key(),
    result.replace_error(
      (
        "Request does not have necessary authorization credentials, "
        + "must provide Places API Key",
        HTTPStatus.UNAUTHORIZED,
      )
    ),
    result.unwrap(),
  )

  search_nearby_response = places_session.post(
    API_URL + SEARCH_NEARBY_ENDPOINT,
    json=api_request_model.model_dump(),
    headers={"X-Goog-Api-Key": places_api_key},
  )

  return pipe(
    search_nearby_response,
    parse_response_json,
    result.unwrap(),
  )


@result.with_unwrap
def handle_response(
  response_body: dict[str, Any],
) -> Result[NearbySearchPlacesApiResponse, str]:
  return pipe(
    decode_model(NearbySearchPlacesApiResponse, response_body),
    result.unwrap(),
    Ok,
  )
