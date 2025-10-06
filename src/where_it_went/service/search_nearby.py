import typing as t
from http import HTTPMethod, HTTPStatus

import flask
import requests
from flask import Blueprint, jsonify, request
from pydantic import BaseModel, Field

from where_it_went import config

from ..utils import pipe, result
from ..utils.decoding import decode_model
from ..utils.http import parse_get_json, parse_response_json
from ..utils.result import Err, Ok, Result
from .redis_caching import fetch_or_cache_region

search_nearby_blueprint = Blueprint("search_nearby", __name__)

API_URL = "https://places.googleapis.com/v1"
SEARCH_NEARBY_ENDPOINT = "/places:searchNearby"

places_session = requests.Session()
places_session.headers.update(
  {
    "Content-Type": "application/json",
    "X-Goog-FieldMask": "places.displayName,places.location,places.types,places.formattedAddress,places.addressComponents",  # noqa: E501
  }
)


class SearchNearbyRequest(BaseModel):
  latitude: float
  longitude: float
  radius: float  # meters


class DisplayName(BaseModel):
  language_code: str = Field(..., alias="languageCode")
  text: str


class Location(BaseModel):
  latitude: float
  longitude: float


class AddressComponent(BaseModel):
  long_text: str = Field(..., alias="longText")
  short_text: str = Field(..., alias="shortText")
  types: list[str]


class ApiPlace(BaseModel):
  display_name: DisplayName = Field(..., alias="displayName")
  location: Location
  types: list[str]
  formatted_address: str | None = Field(None, alias="formattedAddress")
  address_components: list[AddressComponent] | None = Field(
    None, alias="addressComponents"
  )


class NearbySearchPlacesApiResponse(BaseModel):
  places: list[ApiPlace]


class ResponsePlace(BaseModel):
  text: str
  latitude: float
  longitude: float
  types: list[str]


class NearbySearchResponse(BaseModel):
  places: list[ResponsePlace]


def _fetch_places_from_api(
  latitude: float, longitude: float, radius: float, api_key: str
) -> dict[str, list[dict[str, t.Any]]]:
  """Fetch places from Google Places API and return raw dict for caching."""
  search_nearby_request_body = {
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
  }

  search_nearby_response = places_session.post(
    API_URL + SEARCH_NEARBY_ENDPOINT,
    json=search_nearby_request_body,
    headers={"X-Goog-Api-Key": api_key},
  )

  response_body = pipe(
    search_nearby_response,
    parse_response_json,
    result.map_error(lambda e: (e, HTTPStatus.BAD_REQUEST)),
    result.unwrap(),
  )

  api_response_model = pipe(
    decode_model(NearbySearchPlacesApiResponse, response_body),
    result.map_error(lambda e: (e, HTTPStatus.BAD_REQUEST)),
    result.unwrap(),
  )

  # Converting to dict format for caching
  places_data = [
    {
      "text": api_place.display_name.text,
      "latitude": api_place.location.latitude,
      "longitude": api_place.location.longitude,
      "types": api_place.types,
    }
    for api_place in api_response_model.places
  ]

  return {"places": places_data}


@result.with_unwrap
def do_search_nearby(
  request: flask.Request,
) -> Result[NearbySearchResponse, tuple[str, HTTPStatus]]:
  request_body = pipe(
    request,
    parse_get_json,
    result.map_error(lambda e: (e, HTTPStatus.BAD_REQUEST)),
    result.unwrap(),
  )

  model = pipe(
    decode_model(SearchNearbyRequest, request_body),
    result.map_error(lambda e: (e, HTTPStatus.BAD_REQUEST)),
    result.unwrap(),
  )

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

  cached_result = fetch_or_cache_region(
    latitude=model.latitude,
    longitude=model.longitude,
    radius=model.radius,
    caller=lambda: _fetch_places_from_api(
      model.latitude, model.longitude, model.radius, places_api_key
    ),
    filter_by_distance=True,
  )

  # Converting cached result to response model as we return it to the client
  match cached_result:
    case Ok(cached_data):
      places = [
        ResponsePlace(**place_data) for place_data in cached_data["places"]
      ]
      response_model = NearbySearchResponse(places=places)
      return Ok(response_model)
    case Err(error):
      return Err((f"Cache error: {error}", HTTPStatus.INTERNAL_SERVER_ERROR))


@search_nearby_blueprint.route("/search-nearby", methods=[HTTPMethod.GET])
def search_nearby() -> tuple[flask.Response, HTTPStatus]:
  match do_search_nearby(request):
    case Ok(model):
      return jsonify(model.model_dump()), HTTPStatus.OK
    case Err((e, status)):
      return jsonify({"error": e}), status
