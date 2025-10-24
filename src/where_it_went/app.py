import html
import os
import re
from http import HTTPMethod, HTTPStatus

import flask
import google.generativeai as gemini
from flask import Flask, jsonify, request
from pydantic import BaseModel

from where_it_went.service.search_nearby import search_nearby_blueprint
from where_it_went.service.usa_spending_service import (
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

# Configure Gemini API
gemini.configure(api_key="AIzaSyD0y_yBgtqGhzkvVSpJRTytoB4wJRkAxGk")

app = Flask(__name__)
app.register_blueprint(search_nearby_blueprint)
usa_spending_client: USASpendingClient = USASpendingClient()


class AddRequest(BaseModel):
  x: int
  y: int


@app.route("/health", methods=[HTTPMethod.GET])
def health_check() -> tuple[flask.Response, HTTPStatus]:
  """Health check endpoint for Docker."""
  return jsonify(
    {"status": "healthy", "service": "where-it-went"}
  ), HTTPStatus.OK


@app.route("/add", methods=[HTTPMethod.POST])
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


@app.route(rule="/search-spending-by-award", methods=[HTTPMethod.GET])
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


def clean_text(text: str) -> str:
  """Convert markdown gemini response to HTML and clean text."""
  # Decode HTML entities
  text = html.unescape(text)
  # Convert section headers to proper format
  text = re.sub(r'\*\*(Key Findings|Breakdown|Insights):\*\*', r'<h4>\1:</h4>', text)
  # Convert other bold text
  text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
  # Convert bullet points
  text = re.sub(r'\u2022\s*(.*)', r'<li>\1</li>', text)
  text = re.sub(r'(<li>.*</li>)', r'<ul>\1</ul>', text)
  text = re.sub(r'</ul>\s*<ul>', '', text)
  text = text.strip()
  return text


@app.route("/api/generate-summary", methods=[HTTPMethod.POST])
def generate_summary() -> tuple[flask.Response, HTTPStatus]:
  """Generate AI summary of spending data using Gemini API."""
  try:
    data = request.get_json()
    spending_results = data.get('data', [])
    
    if not spending_results:
      return jsonify({"error": "No data provided"}), HTTPStatus.BAD_REQUEST
    
    # Prepare data summary for Gemini
    total_amount = sum(item['award_amount'] for item in spending_results)
    agencies = list(set(item['awarding_agency'] for item in spending_results))
    recipients = list(set(item['recipient_name'] for item in spending_results))
    
    prompt = f"""
    Analyze this federal spending data and provide a direct, structured summary:
    
    Data: {len(spending_results)} records, ${total_amount:,.2f} total
    Agencies: {', '.join(agencies[:3])}
    Recipients: {', '.join(recipients[:3])}
    
    Provide a summary in this exact format:
    
    **Key Findings:**
    [2-3 sentence overview of main patterns]
    
    **Breakdown:**
    • Top agency and percentage of total funding
    • Largest recipient and their total amount
    • Notable project types or focus areas
    
    **Insights:**
    • [Key insight 1]
    • [Key insight 2]
    
    Keep it under 150 words, direct and factual.
    """
    
    model = gemini.GenerativeModel('gemini-2.5-pro')
    response = model.generate_content(prompt)
    
    cleaned_summary = clean_text(response.text)
    return jsonify({"summary": cleaned_summary}), HTTPStatus.OK
    
  except Exception as e:
    return jsonify({"summary": f"Unable to generate summary: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
