"""USA Spending API integration for federal spending data."""

from __future__ import annotations

from typing import Any, Literal, Self

import requests
from pydantic import BaseModel, Field

from where_it_went.utils import pipe, result
from where_it_went.utils.decoding import decode_model
from where_it_went.utils.http import parse_response_json
from where_it_went.utils.result import Ok, Result


class PlaceOfPerformance(BaseModel):
  """Represents a place of performance location."""

  country: str = Field(..., description="Country code (e.g., 'USA')")
  state: str = Field(..., description="State abbreviation (e.g., 'VA')")
  zip: str = Field(..., description="ZIP code (e.g., '22030')")


class SpendingFilters(BaseModel):
  """Filters for USA Spending API search."""

  award_type_codes: list[str] = Field(
    default_factory=lambda: ["A", "B", "C", "D"]
  )
  recipient_search_text: list[str] = Field(default_factory=list)
  place_of_performance_locations: list[PlaceOfPerformance] = Field(
    default_factory=list
  )


class SpendingRequest(BaseModel):
  """Request model for USA Spending API."""

  filters: SpendingFilters
  fields: list[str] = Field(
    default_factory=lambda: [
      "Award ID",
      "Recipient Name",
      "Award Amount",
      "Awarding Agency",
      "Start Date",
      "End Date",
      "Place of Performance Zip5",
      "Description",
    ]
  )
  limit: int = Field(default=10, description="Number of awards per page")
  page: int = Field(default=1, description="Page number")
  subawards: bool = Field(default=False)
  sort: str = Field(default="Award Amount")
  order: Literal["asc", "desc"] = Field(default="desc")


class Award(BaseModel):
  """Represents a federal award."""

  award_id: str | None = Field(None, alias="Award ID")
  recipient_name: str | None = Field(None, alias="Recipient Name")
  award_amount: float | None = Field(None, alias="Award Amount")
  awarding_agency: str | None = Field(None, alias="Awarding Agency")
  start_date: str | None = Field(None, alias="Start Date")
  end_date: str | None = Field(None, alias="End Date")
  place_of_performance_zip5: str | None = Field(
    None, alias="Place of Performance Zip5"
  )
  description: str | None = Field(None, alias="Description")


class SpendingResponse(BaseModel):
  """Response model for USA Spending API."""

  results: list[Award]
  page_metadata: dict[str, Any]
  messages: list[str] = Field(default_factory=list)


class USASpendingError(Exception):
  """Custom exception for USA Spending API errors."""

  pass


class USASpendingClient:
  """Client for interacting with USA Spending API."""

  def __init__(self) -> None:
    self.base_url: str = "https://api.usaspending.gov/api/v2"
    self.client: requests.Session = requests.Session()

  def __enter__(self) -> Self:
    return self

  def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
    self.client.close()

  @result.with_unwrap
  def search_spending_by_award(
    self,
    request: SpendingRequest,
  ) -> Result[SpendingResponse, Exception]:
    """
    Search for federal spending by award.

    Args:
        request: The spending search request

    Returns:
        Result containing spending response or error
    """
    url = f"{self.base_url}/search/spending_by_award/"

    # Convert Pydantic model to dict and handle nested models
    request_data = request.model_dump(by_alias=True, exclude_none=True)

    response = self.client.post(
      url,
      json=request_data,
      headers={"Content-Type": "application/json"},
    )
    response_body = pipe(
      response,
      parse_response_json,
      result.map_error(lambda e: USASpendingError(f"HTTP error: {e}")),
      result.unwrap(),
    )

    # Parse the response
    spending_response = pipe(
      decode_model(SpendingResponse, response_body),
      result.map_error(lambda e: USASpendingError(f"Decoding error: {e}")),
      result.unwrap(),
    )

    return Ok(spending_response)

  def create_location_search(
    self,
    recipient_search: str | None = None,
    locations: list[PlaceOfPerformance] | None = None,
    award_types: list[str] | None = None,
    limit: int = 10,
    page: int = 1,
  ) -> SpendingRequest:
    """
    Create a spending search request for specific locations.

    Args:
        recipient_search: Text to search for in recipient names
        locations: List of places of performance
        award_types: List of award type codes
        limit: Number of results per page
        page: Page number

    Returns:
        Configured SpendingRequest
    """
    filters = SpendingFilters()

    if recipient_search:
      filters.recipient_search_text = [recipient_search]

    if locations:
      filters.place_of_performance_locations = locations

    if award_types:
      filters.award_type_codes = award_types

    return SpendingRequest(
      filters=filters,
      limit=limit,
      page=page,
    )

  def create_recipient_search(
    self,
    recipient_name: str,
    locations: list[PlaceOfPerformance] | None = None,
    award_types: list[str] | None = None,
    limit: int = 10,
    page: int = 1,
  ) -> SpendingRequest:
    """
    Create a spending search request for a specific recipient.

    Args:
        recipient_name: Name of the recipient to search for
        locations: List of places of performance
        award_types: List of award type codes
        limit: Number of results per page
        page: Page number

    Returns:
        Configured SpendingRequest
    """
    return self.create_location_search(
      recipient_search=recipient_name,
      locations=locations,
      award_types=award_types,
      limit=limit,
      page=page,
    )
