import os

from .utils.result import Err, Ok, Result


def get_port() -> int:
  """
  Retrieve the port the app listens on

  Defaults to 5000 if not present or if not a valid integer
  """
  match os.getenv("PORT"):
    case None:
      return 5000
    case port:
      try:
        return int(port)
      except Exception:
        return 5000


def get_places_api_key() -> Result[str, None]:
  match os.getenv("PLACES_API_KEY"):
    case None:
      return Err(None)
    case key:
      return Ok(key)
