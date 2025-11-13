from http import HTTPMethod, HTTPStatus
from typing import Any

import flask
from flask import Blueprint, jsonify, request
from pydantic import BaseModel, ValidationError

from where_it_went.service.report_service import ReportService
from where_it_went.service.search_places import api
from where_it_went.service.usa_spending import (
  Award,
  PlaceOfPerformance,
  SpendingFilters,
  SpendingRequest,
  SpendingResponse,
  USASpendingClient,
  USASpendingError,
)
from where_it_went.utils import result
from where_it_went.utils.decoding import decode_model
from where_it_went.utils.http import parse_get_json, parse_post_json
from where_it_went.utils.result import Err, Ok, Result

bp = Blueprint("routes", __name__)

report_service: ReportService | None = None


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


# Generate Summary Endpoint
@bp.route("/api/generate-summary", methods=[HTTPMethod.POST])
def generate_summary() -> tuple[flask.Response, HTTPStatus]:
  try:
    raw_data = request.get_json()

    if not raw_data.get("data"):
      return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST

    # Preprocess raw data to match SpendingResponse schema
    transformed_data: dict[str, Any] = {
      "results": [
        {
          "Award ID": award.get("award_id"),
          "Recipient Name": award.get("recipient_name"),
          "Award Amount": award.get("award_amount"),
          "Awarding Agency": award.get("awarding_agency"),
          "Start Date": award.get("start_date"),
          "End Date": award.get("end_date"),
          "Place of Performance Zip5": award.get("place_of_performance_zip5"),
          "Description": award.get("description"),
        }
        for award in raw_data.get("data", [])
      ],
      "page_metadata": {},
    }

    if report_service is None:
      return jsonify(
        {"summary": "AI service not available"}
      ), HTTPStatus.SERVICE_UNAVAILABLE

    spending_response = SpendingResponse(**transformed_data)
    summary_result = report_service.generate_summary(spending_response)

    match summary_result:
      case Ok(summary_text):
        return jsonify({"summary": summary_text}), HTTPStatus.OK
      case Err(error):
        return jsonify(
          {"summary": f"Unable to generate summary: {error}"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR

  except ValidationError:
    return jsonify({"error": "Invalid input data"}), HTTPStatus.BAD_REQUEST
  except Exception:
    return jsonify(
      {"error": "Internal server error"}
    ), HTTPStatus.INTERNAL_SERVER_ERROR


# Chart Data Processing Endpoint
@bp.route("/api/process-chart-data", methods=[HTTPMethod.POST])
def process_chart_data() -> tuple[flask.Response, HTTPStatus]:
  try:
    data = request.get_json()
    awards_data = data.get("data", [])
    feature = data.get("feature", "award_amount")

    if not awards_data:
      return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST

    if report_service is None:
      return jsonify(
        {"error": "AI service not available"}
      ), HTTPStatus.SERVICE_UNAVAILABLE

    awards = [Award(**award) for award in awards_data]
    processed_data = report_service.process_chart_data(awards, feature)

    return jsonify(processed_data), HTTPStatus.OK

  except Exception as e:
    return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


# Table Data Processing Endpoint
@bp.route("/api/process-table-data", methods=[HTTPMethod.POST])
def process_table_data() -> tuple[flask.Response, HTTPStatus]:
  try:
    data = request.get_json()
    awards_data = data.get("data", [])

    if not awards_data:
      return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST

    formatted_data: list[dict[str, Any]] = []
    for award_data in awards_data:
      formatted_award = {
        "award_id": award_data.get("award_id", "N/A"),
        "award_amount_formatted": f"${award_data.get('award_amount', 0):,.2f}",
        "award_amount": award_data.get("award_amount"),
        "awarding_agency": award_data.get("awarding_agency", "N/A"),
        "recipient_name": award_data.get("recipient_name", "N/A"),
        "description": award_data.get("description", "N/A"),
        "start_date": award_data.get("start_date", "N/A"),
        "end_date": award_data.get("end_date", "N/A"),
      }
      formatted_data.append(formatted_award)

    return jsonify({"data": formatted_data}), HTTPStatus.OK

  except Exception as e:
    return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


# Text Search Endpoint
@bp.route("/api/text-search", methods=[HTTPMethod.POST])
def text_search() -> tuple[flask.Response, HTTPStatus]:
  """Search for places using Google Text Search API."""
  search_request_result: Result[api.TextSearchRequest, str] = result.do(
    Ok(search_request)
    for json in parse_post_json(request)
    for search_request in decode_model(api.TextSearchRequest, json)
  )

  match search_request_result:
    case Ok(search_request):
      try:
        # Build API request
        api_request = api.build_text_search_api_request(
          text_query=search_request.text_query
        )

        # Send request to Google Places API
        response_result = api.send_text_search_request(api_request)
        match response_result:
          case Ok(response_body):
            # Handle the response
            api_response_result = api.handle_text_search_response(response_body)
            match api_response_result:
              case Ok(api_response):
                # Convert API places to dict format for JSON response
                places_data = [
                  place.model_dump() for place in api_response.places
                ]

                return jsonify(
                  {"places": places_data, "count": len(places_data)}
                ), HTTPStatus.OK
              case Err(error):
                return jsonify(
                  {"error": f"Failed to parse API response: {error}"}
                ), HTTPStatus.BAD_REQUEST
          case Err(error):
            return jsonify(
              {"error": f"API request failed: {error}"}
            ), HTTPStatus.BAD_REQUEST

      except Exception as e:
        return jsonify(
          {"error": f"Internal server error: {e}"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR

    case Err(e):
      return jsonify({"error": e}), HTTPStatus.BAD_REQUEST


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
