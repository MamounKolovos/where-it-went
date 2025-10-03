from http import HTTPMethod, HTTPStatus
from typing import Any

import flask
import requests
from flask import Blueprint, jsonify, request
from pydantic import BaseModel, Field

from where_it_went import config

from ..utils import result
from ..utils.decoding import decode_model
from ..utils.http import parse_get_json, parse_response_json
from ..utils.result import Err, Ok, Result

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


class NearbySearchRequest(BaseModel):
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


class Place(BaseModel):
  display_name: DisplayName = Field(..., alias="displayName")
  location: Location
  types: list[str]
  formatted_address: str | None = Field(None, alias="formattedAddress")
  address_components: list[AddressComponent] | None = Field(
    None, alias="addressComponents"
  )


class NearbySearchPlacesApiResponse(BaseModel):
  places: list[Place]


@search_nearby_blueprint.route("/search-nearby", methods=[HTTPMethod.GET])
def search_nearby() -> tuple[flask.Response, HTTPStatus]:
  model_result: Result[NearbySearchRequest, str] = result.do(
    Ok(model)
    for json in parse_get_json(request)
    for model in decode_model(NearbySearchRequest, json)
  )

  if isinstance(model_result, Err):
    return jsonify({"error": model_result.err_value}), HTTPStatus.BAD_REQUEST

  model = model_result.unwrap()

  json = {
    "locationRestriction": {
      "circle": {
        "center": {
          "latitude": model.latitude,
          "longitude": model.longitude,
        },
        "radius": model.radius,
      }
    },
    "maxResultCount": 20,
  }

  places_api_key_result = config.get_places_api_key()
  if isinstance(places_api_key_result, Err):
    return jsonify(
      {
        "error": "Request does not have necessary authorization credentials, \
        must provide Places API Key"
      }
    ), HTTPStatus.UNAUTHORIZED

  places_api_key = places_api_key_result.unwrap()

  response = places_session.post(
    API_URL + SEARCH_NEARBY_ENDPOINT,
    json=json,
    headers={"X-Goog-Api-Key": places_api_key},
  )

  response_json_result = parse_response_json(response)

  if isinstance(response_json_result, Err):
    return jsonify(
      {"error": response_json_result.err_value}
    ), HTTPStatus.BAD_REQUEST

  response_json = response_json_result.unwrap()

  response_model_result = decode_model(
    NearbySearchPlacesApiResponse, response_json
  )

  if isinstance(response_model_result, Err):
    return jsonify(
      {"error": response_model_result.err_value}
    ), HTTPStatus.BAD_REQUEST

  response_model = response_model_result.unwrap()

  # Extract simplified address info for each place
  simplified_places: list[dict[str, Any]] = []
  for place in response_model.places:
    city = None
    state = None
    zipcode = None

    if place.address_components:
      for component in place.address_components:
        if "locality" in component.types:
          city = component.long_text
        elif "administrative_area_level_1" in component.types:
          state = component.short_text
        elif "postal_code" in component.types:
          zipcode = component.long_text

    # We can add more fields to the response later if we want to
    formatted_response: dict[
      str, str | dict[str, float] | list[str] | dict[str, str | None]
    ] = {
      "display_name": place.display_name.text,
      "location": {
        "latitude": place.location.latitude,
        "longitude": place.location.longitude,
      },
      "types": place.types,
      "address": {"city": city, "state": state, "zipcode": zipcode},
    }
    simplified_places.append(formatted_response)

  return jsonify({"places": simplified_places}), HTTPStatus.OK
