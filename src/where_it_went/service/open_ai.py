import json
import os

from openai import OpenAI

from where_it_went.service.usa_spending import SpendingResponse
from where_it_went.utils.clean_text import cleanText


class OpenAIService:
  def __init__(self) -> None:
    # Initialize the OpenAI client with the API key
    self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not self.client.api_key:
      raise ValueError(
        "OpenAI API key is missing! Please set it in the environment variables."
      )

    # Instructions for the OpenAI model
    self.instructions = """
        - Role:
          You are a federal spending data analyst. Your job is to analyze federal spending data and provide concise, structured summaries.

        - Tasks:
          1. Analyze the provided JSON array of award records.
          2. Identify key patterns, top agencies, recipients, and notable insights.
          3. Summarize the data in a machine-readable format.

        - Input Format:
          JSON object containing:
          - Data: {len(spending_results)} records, ${total_amount:,.2f} total
          - Agencies: {', '.join(agencies[:3])}
          - Recipients: {', '.join(recipients[:3])}

        - Response Format:
          - ALWAYS follow this format:

          **Key Findings:**
          [2-3 sentence overview of main patterns]

          **Breakdown:**
          • Top agency and percentage of total funding
          • Largest recipient and their total amount
          • Notable project types or focus areas

          **Insights:**
          • [Key insight 1]
          • [Key insight 2]
          
          NOTE: the data is 0-indexed
          Keep it under 150 words, direct and factual.
        """
    print("[OpenAIService] Initialized with API key.")

  def generate_report(self, spending_response: SpendingResponse) -> str:
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
        item.award_amount for item in spending_response.results
      )

      # Prepare OpenAI messages
      messages = [
        {"role": "system", "content": self.instructions},
        {
          "role": "user",
          "content": f"Data: {len(spending_response.results)} records, ${total_amount:,.2f} total\n"
          f"Agencies: {', '.join(list({item.awarding_agency for item in spending_response.results})[:3])}\n"
          f"Recipients: {', '.join(list({item.recipient_name for item in spending_response.results})[:3])}\n"
          "Analyze this federal spending data and provide a direct, structured summary.",
        },
      ]

      print("[OpenAIService] Messages prepared for OpenAI API.")

      prompt = f"{self.instructions}\nAnalyze this federal spending data and provide a direct, structured summary:\nData: {len(spending_response.results)} records, ${sum(item.award_amount for item in spending_response.results):,.2f} total\nAgencies: {', '.join(list({item.awarding_agency for item in spending_response.results})[:3])}\nRecipients: {', '.join(list({item.recipient_name for item in spending_response.results})[:3])}\n\nProvide a summary in this exact format:\n\n**Key Findings:**\n[2-3 sentence overview of main patterns]\n\n**Breakdown:**\n• Top agency and percentage of total funding\n• Largest recipient and their total amount\n• Notable project types or focus areas\n\n**Insights:**\n• [Key insight 1]\n• [Key insight 2]\n\nKeep it under 150 words, direct and factual."

      # Call OpenAI API
      response = self.client.chat.completions.create(
        model="gpt-4",
        messages=messages,
        temperature=0.0,
        max_tokens=800,
      )
      print("[OpenAIService] OpenAI API call successful.")

      # Extract and return the summary
      raw_output = response.choices[0].message.content
      formatted_output = cleanText(raw_output)
      return formatted_output
    except Exception as e:
      print(f"[OpenAIService] Error in OpenAIService: {e}")
      raise
