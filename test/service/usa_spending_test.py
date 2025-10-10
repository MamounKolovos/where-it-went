#!/usr/bin/env python3
"""Comprehensive test suite for USA Spending API service."""

import sys
from pathlib import Path
from typing import Any

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from where_it_went.service.usa_spending_service import (
  Award,
  PlaceOfPerformance,
  SpendingFilters,
  SpendingRequest,
  SpendingResponse,
  USASpendingClient,
)
from where_it_went.utils.result import Err, Ok

# Using pytest test functions


def place_of_performance_model_test() -> None:
  """Test PlaceOfPerformance model creation and validation."""
  print("🧪 Testing PlaceOfPerformance model...")

  # Test valid creation
  location = PlaceOfPerformance(country="USA", state="VA", zip="22030")
  assert location.country == "USA"
  assert location.state == "VA"
  assert location.zip == "22030"

  # Test model_dump
  data = location.model_dump()
  assert data["country"] == "USA"
  assert data["state"] == "VA"
  assert data["zip"] == "22030"

  print("✅ Model creation and serialization works")


def test_spending_filters_model() -> None:
  """Test SpendingFilters model creation and defaults."""
  print("🧪 Testing SpendingFilters model...")

  # Test default creation
  filters = SpendingFilters()
  assert filters.award_type_codes == ["A", "B", "C", "D"]
  assert filters.recipient_search_text == []
  assert filters.place_of_performance_locations == []

  # Test with custom values
  locations = [PlaceOfPerformance(country="USA", state="VA", zip="22030")]
  filters = SpendingFilters(
    award_type_codes=["A", "B"],
    recipient_search_text=["Test University"],
    place_of_performance_locations=locations,
  )
  assert len(filters.award_type_codes) == 2
  assert len(filters.recipient_search_text) == 1
  assert len(filters.place_of_performance_locations) == 1

  print("✅ Filters model works correctly")


def spending_request_model_test() -> None:
  """Test SpendingRequest model creation and defaults."""
  print("🧪 Testing SpendingRequest model...")

  filters = SpendingFilters()
  request = SpendingRequest(filters=filters)

  # Test defaults
  assert request.limit == 10
  assert request.page == 1
  assert not request.subawards
  assert request.sort == "Award Amount"
  assert request.order == "desc"
  assert len(request.fields) == 8  # Default fields

  # Test model_dump with by_alias
  data = request.model_dump(by_alias=True)
  assert "filters" in data
  assert "limit" in data
  assert "page" in data

  print("✅ Request model works correctly")


def award_model_test() -> None:
  """Test Award model with aliases."""
  print("🧪 Testing Award model...")

  # Test creation with aliases
  award_data: dict[str, Any] = {
    "Award ID": "12345",
    "Recipient Name": "Test University",
    "Award Amount": 100000.0,
    "Awarding Agency": "Test Agency",
    "Start Date": "2023-01-01",
    "End Date": "2023-12-31",
    "Place of Performance Zip5": "22030",
    "Description": "Test award",
  }

  award = Award(**award_data)
  assert award.award_id == "12345"
  assert award.recipient_name == "Test University"
  assert award.award_amount == 100000.0

  # Test model_dump with aliases
  data = award.model_dump(by_alias=True)
  assert data["Award ID"] == "12345"
  assert data["Recipient Name"] == "Test University"

  print("✅ Award model with aliases works")


def spending_response_model_test() -> None:
  """Test SpendingResponse model."""
  print("🧪 Testing SpendingResponse model...")

  award_data: dict[str, Any] = {
    "Award ID": "123",
    "Recipient Name": "Test",
    "Award Amount": 1000.0,
  }
  awards = [Award(**award_data)]
  response = SpendingResponse(
    results=awards,
    page_metadata={"total": 1, "page": 1},
    messages=["Test message"],
  )

  assert len(response.results) == 1
  assert response.page_metadata["total"] == 1
  assert len(response.messages) == 1

  print("✅ Response model works correctly")


def client_initialization_test() -> None:
  """Test USASpendingClient initialization and context manager."""
  print("🧪 Testing USASpendingClient initialization...")

  # Test initialization
  client = USASpendingClient()
  assert client.base_url == "https://api.usaspending.gov/api/v2"
  assert client.client is not None

  # Test context manager
  with USASpendingClient() as ctx_client:
    assert ctx_client.base_url == "https://api.usaspending.gov/api/v2"

  print("✅ Client initialization and context manager work")


def create_location_search_test() -> None:
  """Test create_location_search method."""
  print("🧪 Testing create_location_search method...")

  with USASpendingClient() as client:
    # Test with no parameters (defaults)
    request = client.create_location_search()
    assert request.limit == 10
    assert request.page == 1
    assert len(request.filters.award_type_codes) == 4

    # Test with recipient search
    request = client.create_location_search(recipient_search="Test University")
    assert request.filters.recipient_search_text == ["Test University"]

    # Test with locations
    locations = [PlaceOfPerformance(country="USA", state="VA", zip="22030")]
    request = client.create_location_search(locations=locations)
    assert len(request.filters.place_of_performance_locations) == 1

    # Test with award types
    request = client.create_location_search(award_types=["A", "B"])
    assert request.filters.award_type_codes == ["A", "B"]

    # Test with custom limit and page
    request = client.create_location_search(limit=5, page=2)
    assert request.limit == 5
    assert request.page == 2

  print("✅ create_location_search method works correctly")


def create_recipient_search_test() -> None:
  """Test create_recipient_search method."""
  print("🧪 Testing create_recipient_search method...")

  with USASpendingClient() as client:
    # Test basic recipient search
    request = client.create_recipient_search("Test University")
    assert request.filters.recipient_search_text == ["Test University"]

    # Test with locations
    locations = [PlaceOfPerformance(country="USA", state="VA", zip="22030")]
    request = client.create_recipient_search(
      "Test University", locations=locations
    )
    assert request.filters.recipient_search_text == ["Test University"]
    assert len(request.filters.place_of_performance_locations) == 1

    # Test with award types
    request = client.create_recipient_search(
      "Test University", award_types=["A"]
    )
    assert request.filters.award_type_codes == ["A"]

  print("✅ create_recipient_search method works correctly")


def spending_by_award_api_test() -> None:
  """Test the exact same request as the PowerShell script."""
  print("🧪 Testing PowerShell-equivalent George Mason search...")

  # Example location for testing
  locations = [
    PlaceOfPerformance(country="USA", state="VA", zip="22030"),
    PlaceOfPerformance(country="USA", state="VA", zip="22150"),
  ]

  # Create the filters
  filters = SpendingFilters(
    award_type_codes=["A", "B", "C", "D"],
    recipient_search_text=["George Mason University"],
    place_of_performance_locations=locations,
  )

  # Create the full request
  request = SpendingRequest(
    filters=filters,
    fields=[
      "Award ID",
      "Recipient Name",
      "Award Amount",
      "Awarding Agency",
      "Start Date",
      "End Date",
      "Place of Performance Zip5",
      "Description",
    ],
    limit=10,
    page=1,
    subawards=False,
    sort="Award Amount",
    order="desc",
  )

  # Make the API call
  with USASpendingClient() as client:
    result = client.search_spending_by_award(request)

    match result:
      case Ok(spending_response):
        assert len(spending_response.results) > 0
        print(
          f"✅ API call succeeded with {len(spending_response.results)} results"
        )
        for award in spending_response.results:
          print(
            (
              f"- {award.recipient_name} received ${award.award_amount} "
              f"for award ID {award.award_id}"
            )
          )
      case Err(error):
        pytest.fail(f"API call failed: {error}")
