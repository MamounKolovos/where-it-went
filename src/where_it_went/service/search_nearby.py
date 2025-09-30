from http import HTTPMethod, HTTPStatus

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


class Place(BaseModel):
  display_name: DisplayName = Field(..., alias="displayName")
  location: Location
  types: list[str]


class NearbySearchPlacesApiResponse(BaseModel):
  places: list[Place]


API_URL = "https://places.googleapis.com/v1"
SEARCH_NEARBY_ENDPOINT = "/places:searchNearby"


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

  headers = {
    "Content-Type": "application/json",
    "X-Goog-FieldMask": "places.displayName,places.location,places.types",
    "X-Goog-Api-Key": places_api_key,
  }

  response = requests.post(
    API_URL + SEARCH_NEARBY_ENDPOINT, json=json, headers=headers
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

  response_body = response_model.model_dump(
    include={
      "places": {
        "__all__": {
          "display_name": {"text"},
          "location": {"latitude", "longitude"},
          "types": True,
        }
      }
    }
  )

  return jsonify(response_body), HTTPStatus.OK
