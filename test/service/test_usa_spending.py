#!/usr/bin/env python3
"""Comprehensive test suite for USA Spending API service."""

import sys
from pathlib import Path
from typing import Any

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


class TestResults:
  """Track test results."""

  def __init__(self):
    self.passed = 0
    self.failed = 0
    self.tests = []

  def add_test(self, name: str, passed: bool, details: str = ""):
    """Add a test result."""
    self.tests.append((name, passed, details))
    if passed:
      self.passed += 1
    else:
      self.failed += 1

  def print_summary(self):
    """Print test summary."""
    print(f"\n📊 Test Summary: {self.passed} passed, {self.failed} failed")
    for name, passed, details in self.tests:
      status = "✅" if passed else "❌"
      print(f"  {status} {name}")
      if details:
        print(f"     {details}")


class USASpendingTestSuite:
  """Comprehensive test suite for USA Spending API service."""

  def __init__(self):
    self.results = TestResults()

  def test_place_of_performance_model(self):
    """Test PlaceOfPerformance model creation and validation."""
    print("🧪 Testing PlaceOfPerformance model...")

    try:
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

      return True, "Model creation and serialization works"
    except Exception as e:
      return False, f"Model test failed: {e}"

  def test_spending_filters_model(self):
    """Test SpendingFilters model creation and defaults."""
    print("🧪 Testing SpendingFilters model...")

    try:
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

      return True, "Filters model works correctly"
    except Exception as e:
      return False, f"Filters test failed: {e}"

  def test_spending_request_model(self):
    """Test SpendingRequest model creation and defaults."""
    print("🧪 Testing SpendingRequest model...")

    try:
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

      return True, "Request model works correctly"
    except Exception as e:
      return False, f"Request test failed: {e}"

  def test_award_model(self):
    """Test Award model with aliases."""
    print("🧪 Testing Award model...")

    try:
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

      return True, "Award model with aliases works"
    except Exception as e:
      return False, f"Award test failed: {e}"

  def test_spending_response_model(self):
    """Test SpendingResponse model."""
    print("🧪 Testing SpendingResponse model...")

    try:
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

      return True, "Response model works correctly"
    except Exception as e:
      return False, f"Response test failed: {e}"

  def test_client_initialization(self):
    """Test USASpendingClient initialization and context manager."""
    print("🧪 Testing USASpendingClient initialization...")

    try:
      # Test initialization
      client = USASpendingClient()
      assert client.base_url == "https://api.usaspending.gov/api/v2"
      assert client.client is not None

      # Test context manager
      with USASpendingClient() as ctx_client:
        assert ctx_client.base_url == "https://api.usaspending.gov/api/v2"

        return True, "Client initialization and context manager work"
    except Exception as e:
      return False, f"Client initialization test failed: {e}"

  def test_create_location_search(self):
    """Test create_location_search method."""
    print("🧪 Testing create_location_search method...")

    try:
      with USASpendingClient() as client:
        # Test with no parameters (defaults)
        request = client.create_location_search()
        assert request.limit == 10
        assert request.page == 1
        assert len(request.filters.award_type_codes) == 4

        # Test with recipient search
        request = client.create_location_search(
          recipient_search="Test University"
        )
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

        return True, "create_location_search method works correctly"
    except Exception as e:
      return False, f"create_location_search test failed: {e}"

  def test_create_recipient_search(self):
    """Test create_recipient_search method."""
    print("🧪 Testing create_recipient_search method...")

    try:
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

        return True, "create_recipient_search method works correctly"
    except Exception as e:
      return False, f"create_recipient_search test failed: {e}"

  def test_spending_by_award_api(self):
    """Test the exact same request as the PowerShell script."""
    print("🧪 Testing PowerShell-equivalent George Mason search...")

    try:
      # Create the locations from your PowerShell request
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
          case Ok(response):
            # Extract the value from Ok
            spending_response: SpendingResponse = response.ok_value  # type: ignore
            print(f"    ✅ Found {len(spending_response.results)} awards")
            if spending_response.results:
              # Show first award details
              first_award = spending_response.results[0]
              amount = first_award.award_amount or 0
              recipient = first_award.recipient_name or "Unknown"
              print(f"    📊 Sample: ${amount:,.2f} to {recipient}")
              return (
                True,
                f"API call successful, found \
                {len(spending_response.results)} awards",
              )
          case Err(error):
            return False, f"API call failed: {error}"

    except Exception as e:
      return False, f"PowerShell equivalent test failed: {e}"

  def run_all_tests(self):
    """Run all tests and return results."""
    print("🚀 USA Spending API Comprehensive Test Suite")
    print("=" * 60)

    # Model tests
    passed, details = self.test_place_of_performance_model()
    self.results.add_test("PlaceOfPerformance Model", passed, details)

    passed, details = self.test_spending_filters_model()
    self.results.add_test("SpendingFilters Model", passed, details)

    passed, details = self.test_spending_request_model()
    self.results.add_test("SpendingRequest Model", passed, details)

    passed, details = self.test_award_model()
    self.results.add_test("Award Model", passed, details)

    passed, details = self.test_spending_response_model()
    self.results.add_test("SpendingResponse Model", passed, details)

    # Client tests
    passed, details = self.test_client_initialization()
    self.results.add_test("Client Initialization", passed, details)

    passed, details = self.test_create_location_search()
    self.results.add_test("create_location_search Method", passed, details)

    passed, details = self.test_create_recipient_search()
    self.results.add_test("create_recipient_search Method", passed, details)

    # API tests

    passed, details = self.test_spending_by_award_api()
    self.results.add_test("PowerShell Equivalent", passed, details)

    self.results.print_summary()

    return self.results.failed == 0


if __name__ == "__main__":
  test_suite = USASpendingTestSuite()
  success = test_suite.run_all_tests()
  if success:
    print("\n🎉 All tests passed!")
    sys.exit(0)
  else:
    print("\n❌ Some tests failed!")
    sys.exit(1)
