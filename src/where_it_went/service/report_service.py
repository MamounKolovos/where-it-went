from typing import Any, Dict, List

from where_it_went.service.open_ai import OpenAIService
from where_it_went.service.usa_spending import Award, SpendingResponse
from where_it_went.utils.result import Err, Ok, Result


class ReportService:
  def __init__(self):
    self.openai_service = OpenAIService()

  def process_chart_data(
    self, awards: List[Award], feature: str
  ) -> Dict[str, Any]:
    if feature == "award_amount":
      ranges = [
        {"label": "Under $1M", "min": 0, "max": 1000000},
        {"label": "$1M - $5M", "min": 1000000, "max": 5000000},
        {"label": "$5M - $20M", "min": 5000000, "max": 20000000},
        {"label": "Over $20M", "min": 20000000, "max": float("inf")},
      ]

      counts = []
      for range_item in ranges:
        count = sum(
          1
          for award in awards
          if award.award_amount
          and range_item["min"] <= award.award_amount < range_item["max"]
        )
        counts.append(count)

      return {"labels": [r["label"] for r in ranges], "data": counts}
    else:
      grouped = {}
      for award in awards:
        key = getattr(award, feature, "Unknown") or "Unknown"
        grouped[key] = grouped.get(key, 0) + 1

      return {"labels": list(grouped.keys()), "data": list(grouped.values())}

  def generate_summary(
    self, spending_response: SpendingResponse
  ) -> Result[str, str]:
    try:
      summary = self.openai_service.generate_report(spending_response)
      return Ok(summary)
    except Exception as e:
      return Err(f"Error generating summary: {str(e)}")
