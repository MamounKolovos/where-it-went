from typing import Any

from where_it_went.service.open_ai import OpenAIService
from where_it_went.service.usa_spending import Award, SpendingResponse
from where_it_went.utils.result import Err, Ok, Result


class ReportService:
  openai_service: OpenAIService

  def __init__(self, openai_service: OpenAIService):
    self.openai_service = openai_service

  def process_chart_data(
    self, awards: list[Award], feature: str
  ) -> dict[str, Any]:
    if feature == "award_amount":
      ranges = [
        {"label": "Under $1M", "min": 0, "max": 1000000},
        {"label": "$1M - $5M", "min": 1000000, "max": 5000000},
        {"label": "$5M - $20M", "min": 5000000, "max": 20000000},
        {"label": "Over $20M", "min": 20000000, "max": float("inf")},
      ]

      counts: list[int] = []
      for range_item in ranges:
        count = sum(
          1
          for award in awards
          if award.award_amount
          and int(range_item["min"])
          <= int(award.award_amount)
          < int(range_item["max"])
        )
        counts.append(count)

      return {"labels": [r["label"] for r in ranges], "data": counts}
    else:
      grouped: dict[str, int] = {}
      for award in awards:
        key = getattr(award, feature, "Unknown") or "Unknown"
        grouped[key] = grouped.get(key, 0) + 1

      return {"labels": list(grouped.keys()), "data": list(grouped.values())}

  def generate_summary(
    self, spending_response: SpendingResponse
  ) -> Result[str, str]:
    try:
      result = self.openai_service.generate_report(spending_response)
      match result:
        case Ok(text) if text is not None:
          return Ok(text)
        case Ok(None):
          return Err("OpenAI returned empty response")
        case Err(error):
          return Err(error)
        case _:
          return Err("Unexpected result type")
    except Exception as e:
      return Err(f"Error generating summary: {str(e)}")
