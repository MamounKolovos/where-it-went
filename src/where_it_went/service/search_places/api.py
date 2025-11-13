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
TEXT_SEARCH_ENDPOINT = "/places:searchText"
AUTOCOMPLETE_ENDPOINT = "/places:autocomplete"

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


# ============= TEXT SEARCH API =============


class TextSearchRequest(BaseModel):
  text_query: str


class TextSearchApiRequest(BaseModel):
  text_query: str = Field(..., alias="textQuery")
  language_code: str = Field(default="en", alias="languageCode")
  region_code: str = Field(default="US", alias="regionCode")
  max_result_count: int = Field(default=10, alias="maxResultCount")


class TextSearchApiResponse(BaseModel):
  places: list[ApiPlace] = []


def build_text_search_api_request(text_query: str) -> TextSearchApiRequest:
  request_dict: dict[str, Any] = {
    "textQuery": text_query,
    "languageCode": "en",
    "regionCode": "US",
    "maxResultCount": 10,
  }
  return TextSearchApiRequest(**request_dict)


@result.with_unwrap
def send_text_search_request(
  api_request_model: TextSearchApiRequest,
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

  # Text Search requires specific field mask
  text_search_session = requests.Session()
  text_search_session.headers.update(
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

  text_search_response = text_search_session.post(
    API_URL + TEXT_SEARCH_ENDPOINT,
    json=api_request_model.model_dump(by_alias=True),
    headers={"X-Goog-Api-Key": places_api_key},
  )

  return pipe(
    text_search_response,
    parse_response_json,
    result.unwrap(),
  )


@result.with_unwrap
def handle_text_search_response(
  response_body: dict[str, Any],
) -> Result[TextSearchApiResponse, str]:
  return pipe(
    decode_model(TextSearchApiResponse, response_body),
    result.unwrap(),
    Ok,
  )


# ============= AUTOCOMPLETE API =============


class AutocompleteRequest(BaseModel):
  input: str


class AutocompleteApiRequest(BaseModel):
  input: str
  language_code: str = Field(default="en", alias="languageCode")
  region_code: str = Field(default="US", alias="regionCode")
  include_query_predictions: bool = Field(
    default=False, alias="includeQueryPredictions"
  )


class FormattableText(BaseModel):
  text: str


class StructuredFormat(BaseModel):
  main_text: FormattableText = Field(..., alias="mainText")
  secondary_text: FormattableText = Field(..., alias="secondaryText")


class PlacePrediction(BaseModel):
  place: str
  place_id: str = Field(..., alias="placeId")
  text: FormattableText
  structured_format: StructuredFormat = Field(..., alias="structuredFormat")
  types: list[str] = []


class Suggestion(BaseModel):
  place_prediction: PlacePrediction | None = Field(
    None, alias="placePrediction"
  )


class AutocompleteApiResponse(BaseModel):
  suggestions: list[Suggestion] = []


def build_autocomplete_api_request(input_text: str) -> AutocompleteApiRequest:
  request_dict: dict[str, Any] = {
    "input": input_text,
    "languageCode": "en",
    "regionCode": "US",
    "includeQueryPredictions": False,  # Only place predictions
  }
  return AutocompleteApiRequest(**request_dict)


@result.with_unwrap
def send_autocomplete_request(
  api_request_model: AutocompleteApiRequest,
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

  # Autocomplete session
  autocomplete_session = requests.Session()
  autocomplete_session.headers.update(
    {
      "Content-Type": "application/json",
    }
  )

  autocomplete_response = autocomplete_session.post(
    API_URL + AUTOCOMPLETE_ENDPOINT,
    json=api_request_model.model_dump(by_alias=True),
    headers={"X-Goog-Api-Key": places_api_key},
  )

  return pipe(
    autocomplete_response,
    parse_response_json,
    result.unwrap(),
  )


@result.with_unwrap
def handle_autocomplete_response(
  response_body: dict[str, Any],
) -> Result[AutocompleteApiResponse, str]:
  return pipe(
    decode_model(AutocompleteApiResponse, response_body),
    result.unwrap(),
    Ok,
  )
