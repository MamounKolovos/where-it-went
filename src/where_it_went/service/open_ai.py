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

    self.instructions = """
        - Role:


        - Tasks:


        - Input Format:


        - Repsonse Format:
            - ALWAYS fllow this format:

    """

  @result.with_unwrap
  def generate_report(
    self, spending_response: SpendingResponse
  ) -> Result[str | None, str]:
    prompt = str.join(
      "\n",
      [
        self.instructions,
        spending_response.model_dump_json(),
      ],
    )
    response = self.openai_client.chat.completions.create(
      model="gpt-4o-mini",
      messages=[{"role": "user", "content": prompt}],
    )
    return Ok(response.choices[0].message.content)
