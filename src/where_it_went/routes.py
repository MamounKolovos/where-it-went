from http import HTTPMethod, HTTPStatus

import flask
from flask import Blueprint, jsonify, request
from pydantic import BaseModel

# from where_it_went.service.search_places import api
from where_it_went.service.usa_spending import (
  PlaceOfPerformance,
  SpendingFilters,
  SpendingRequest,
  USASpendingClient,
  USASpendingError,
)
from where_it_went.utils import result
from where_it_went.utils.decoding import decode_model
from where_it_went.utils.http import parse_get_json, parse_post_json
from where_it_went.utils.result import Err, Ok, Result

bp = Blueprint("routes", __name__)


class AddRequest(BaseModel):
  x: int
  y: int


@bp.route("/health", methods=[HTTPMethod.GET])
def health_check() -> tuple[flask.Response, HTTPStatus]:
  """Health check endpoint for Docker."""
  return jsonify(
    {"status": "healthy", "service": "where-it-went"}
  ), HTTPStatus.OK


@bp.route("/add", methods=[HTTPMethod.POST])
def add() -> tuple[flask.Response, HTTPStatus]:
  add_request_result: Result[AddRequest, str] = result.do(
    Ok(add_request)
    for json in parse_post_json(request)
    for add_request in decode_model(AddRequest, json)
  )

  match add_request_result:
    case Ok(add_request):
      sum = add_request.x + add_request.y
      return jsonify({"sum": sum}), HTTPStatus.OK
    case Err(e):
      return jsonify({"error": e}), HTTPStatus.BAD_REQUEST


@bp.route(rule="/search-spending-by-award", methods=[HTTPMethod.GET])
def search_spending_by_award() -> tuple[flask.Response, HTTPStatus]:
  """Search for federal spending by award using USA Spending API."""
  args_result: Result[dict[str, str], str] = parse_get_json(request)
  match args_result:
    case Err(error):
      return jsonify({"error": error}), HTTPStatus.BAD_REQUEST
    case Ok(args):
      print(f"DEBUG: Received args: {args}")

      try:
        # Creating spending request from query parameters
        # we can customize this later based on what
        # parameters we want to support
        spending_request: SpendingRequest = SpendingRequest(
          filters=SpendingFilters()
        )
        has_filters = False
        if "recipient" in args:
          spending_request.filters.recipient_search_text = [args["recipient"]]
          has_filters = True
        if "state" in args and "zip" in args:
          location: PlaceOfPerformance = PlaceOfPerformance(
            country="USA",
            state=args["state"],
            zip=args["zip"],
          )
          spending_request.filters.place_of_performance_locations = [location]
          has_filters = True
        if not has_filters:
          return jsonify(
            {"error": "At least one filter is required."}
          ), HTTPStatus.BAD_REQUEST

        with USASpendingClient() as client:
          result = client.search_spending_by_award(request=spending_request)
        match result:
          case Ok(spending_response):
            return jsonify(spending_response.model_dump()), HTTPStatus.OK
          case Err(error):
            return jsonify(
              USASpendingError(f"Decoding error: {error}")
            ), HTTPStatus.BAD_REQUEST

      except Exception as e:
        return jsonify(
          {"error": f"Internal server error: {e}"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR


# Just for testing the Google Places API endpoint

# @bp.route(rule="/search-nearby", methods=[HTTPMethod.POST])
# def search_nearby() -> tuple[flask.Response, HTTPStatus]:
#   """Search for nearby places using Google Places API."""
#   search_request_result: Result[api.SearchNearbyRequest, str] = result.do(
#     Ok(search_request)
#     for json in parse_post_json(request)
#     for search_request in decode_model(api.SearchNearbyRequest, json)
#   )

#   match search_request_result:
#     case Ok(search_request):
#       try:
#         # Build API request
#         api_request = api.build_api_request(
#           latitude=search_request.latitude,
#           longitude=search_request.longitude,
#           radius=search_request.radius,
#         )

#         # Send request to Google Places API
#         response_result = api.send_request(api_request)
#         match response_result:
#           case Ok(response_body):
#             # Handle the response
#             api_response_result = api.handle_response(response_body)
#             match api_response_result:
#               case Ok(api_response):
#                 # Convert API places to dict format for JSON response
#                 places_data = [
#                   place.model_dump() for place in api_response.places
#                 ]

#                 return jsonify(
#                   {"places": places_data, "count": len(places_data)}
#                 ), HTTPStatus.OK
#               case Err(error):
#                 return jsonify(
#                   {"error": f"Failed to parse API response: {error}"}
#                 ), HTTPStatus.BAD_REQUEST
#           case Err(error):
#             return jsonify(
#               {"error": f"API request failed: {error}"}
#             ), HTTPStatus.BAD_REQUEST

#       except Exception as e:
#         return jsonify(
#           {"error": f"Internal server error: {e}"}
#         ), HTTPStatus.INTERNAL_SERVER_ERROR

#     case Err(e):
#       return jsonify({"error": e}), HTTPStatus.BAD_REQUEST
