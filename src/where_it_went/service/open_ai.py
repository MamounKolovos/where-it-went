import json
from http import HTTPStatus

import openai

from where_it_went.config import get_open_ai_api_key
from where_it_went.service.usa_spending import SpendingResponse
from where_it_went.utils import pipe, result
from where_it_went.utils.result import Ok, Result


class OpenAIService:
  openai_client: openai.OpenAI
  instructions: str

  def __init__(self) -> None:
    open_ai_api_key = pipe(
      get_open_ai_api_key(),
      result.replace_error(
        (
          "Request does not have necessary authorization credentials, "
          + "must provide OpenAI API Key",
          HTTPStatus.UNAUTHORIZED,
        )
      ),
      result.unwrap(),
    )
    openai_client = openai.OpenAI(api_key=open_ai_api_key)
    self.openai_client = openai_client

    # Instructions for the OpenAI model
    self.instructions = """
        Role:
        You are a federal spending data analyst. Your job is to analyze federal spending data
        and provide concise, structured summaries.

        Tasks:
        1. Analyze the provided JSON array of award records.
        2. Identify key patterns, top agencies, recipients, and notable insights.
        3. Summarize the data in a structured format.

        - Input Format:
          JSON object containing:
          - Data: {len(spending_results)} records, ${total_amount:,.2f} total
          - Agencies: {', '.join(agencies[:3])}
          - Recipients: {', '.join(recipients[:3])}

        Response Format:
        ALWAYS follow this exact markdown format:

        **Key Findings:**
        [2-3 sentence overview of main patterns]

        **Breakdown:**
        - Top agency and percentage of total funding
        - Largest recipient and their total amount
        - Notable project types or focus areas

        **Insights:**
        - [Key insight 1]
        - [Key insight 2]

        Keep it under 150 words, direct and factual. Use markdown syntax (** for bold, - for bullets).
        DO NOT use HTML tags like <h4>, <ul>, <li> - use markdown only.
        """  # noqa: E501
    print("[OpenAIService] Initialized with API key.")

  def generate_report(
    self, spending_response: SpendingResponse
  ) -> Result[str | None, str]:
    """
    Generates a report summary using OpenAI's API.

    Args:
        spending_response (SpendingResponse): The spending data to analyze.

    Returns:
        str: The generated summary text or raw JSON response.
    """
    try:
      print("[OpenAIService] Preparing to generate report...")

      # Convert SpendingResponse to JSON
      spending_data = spending_response.model_dump_json()
      print(f"[OpenAIService] SpendingResponse JSON: {spending_data}")

      # Calculate the total amount
      total_amount = sum(
        item.award_amount or 0 for item in spending_response.results
      )

      # Extract top agencies and recipients
      agencies = list(
        {item.awarding_agency for item in spending_response.results}
      )[:3]
      recipients = list(
        {item.recipient_name for item in spending_response.results}
      )[:3]

      # Prepare OpenAI messages
      input = [
        {"role": "system", "content": self.instructions},
        {
          "role": "user",
          "content": (
            f"Data: {len(spending_response.results)} records, "
            f"${total_amount:,.2f} total\n"
            f"Agencies: {', '.join(filter(None, agencies))}\n"
            f"Recipients: {', '.join(filter(None, recipients))}\n"
            "Analyze this federal spending data and provide a "
            "direct, structured summary."
          ),
        },
      ]

      print("[OpenAIService] Messages prepared for OpenAI API.")

      # Call OpenAI API
      response = self.openai_client.responses.create(
        model="gpt-4o-mini",
        instructions=self.instructions,
        input=json.dumps(input),
      )
      print("[OpenAIService] OpenAI API call successful.")
      print(f"[OpenAIService] Response type: {type(response)}")
      print(f"[OpenAIService] Response attributes: {dir(response)}")

      raw_output = response.output_text
      print(f"[OpenAIService] Got output_text: {raw_output[:100]}...")
      # Clean up excessive whitespace
      if raw_output:
        import re

        cleaned_output = re.sub(r"\n{3,}", "\n\n", raw_output)  # Max 2 newlines
        return Ok(cleaned_output.strip())
      return Ok(None)
    except Exception as e:
      print(f"[OpenAIService] Error in OpenAIService: {e}")
      print(f"[OpenAIService] Error type: {type(e).__name__}")
      import traceback

      traceback.print_exc()
      raise
