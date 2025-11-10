import os
from http import HTTPMethod, HTTPStatus

import redis
from flask import Flask, jsonify, request
from flask_socketio import SocketIO
from pydantic import ValidationError
from redis import Redis

from where_it_went import routes
from where_it_went.dynamodb_setup import DynamoDBSetup
from where_it_went.service.report_service import ReportService
from where_it_went.service.usa_spending import (
  Award,
  SpendingResponse,
  USASpendingClient,
)
from where_it_went.socket_setup import SocketSetup
from where_it_went.utils.decoding import decode_model
from where_it_went.utils.http import parse_get_json, parse_post_json
from where_it_went.utils.result import Err, Ok, Result

app = Flask(__name__)
app.register_blueprint(routes.bp)
# Use a connection pool to avoid TCP socket race conditions.
# Redis commands are sent over a byte stream, so concurrent writes
# from multiple threads could interleave and corrupt messages.
pool = redis.ConnectionPool(host="redis", port=6379, decode_responses=True)
redis_client = Redis(connection_pool=pool)

# DynamoDB setup
dynamodb_setup = DynamoDBSetup(local=True)


# Initialize report service
usa_spending_client = USASpendingClient()
report_service = ReportService()


# API Endpoints
# Generate Summary Endpoint
@app.route("/api/generate-summary", methods=["POST"])
def generate_summary():
  try:
    # Parse the incoming JSON data
    raw_data = request.get_json()

    # Check if data is provided
    if not raw_data.get("data"):
      return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST

    # Preprocess raw data to match SpendingResponse schema
    transformed_data = {
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
        for award in raw_data.get("data", [])  # Corrected field name
      ],
      "page_metadata": {},
    }

    # Validate and map the data to SpendingResponse
    spending_response = SpendingResponse(**transformed_data)

    # Generate the summary
    summary_result = report_service.generate_summary(spending_response)

    match summary_result:
      case Ok(summary):
        return jsonify({"summary": summary}), HTTPStatus.OK
      case Err(error):
        return jsonify(
          {"summary": f"Unable to generate summary: {error}"}
        ), HTTPStatus.INTERNAL_SERVER_ERROR

  except ValidationError as e:
    return jsonify({"error": "Invalid input data"}), HTTPStatus.BAD_REQUEST
  except Exception as e:
    return jsonify(
      {"error": "Internal server error"}
    ), HTTPStatus.INTERNAL_SERVER_ERROR


# Chart Data Processing Endpoint
@app.route("/api/process-chart-data", methods=[HTTPMethod.POST])
def process_chart_data():
  try:
    data = request.get_json()
    awards_data = data.get("data", [])
    feature = data.get("feature", "award_amount")

    if not awards_data:
      return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST

    awards = [Award(**award) for award in awards_data]
    processed_data = report_service.process_chart_data(awards, feature)

    return jsonify(processed_data), HTTPStatus.OK

  except Exception as e:
    return jsonify({"error": str(e)}), HTTPStatus.INTERNAL_SERVER_ERROR


# Table Data Processing Endpoint
@app.route("/api/process-table-data", methods=[HTTPMethod.POST])
def process_table_data():
  try:
    data = request.get_json()
    awards_data = data.get("data", [])

    if not awards_data:
      return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST

    formatted_data = []
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


socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")
socketio.on_namespace(SocketSetup("/dev", redis_client, dynamodb_setup))
