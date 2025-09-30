from http import HTTPMethod, HTTPStatus
from typing import Any

import flask
import requests
from requests.exceptions import JSONDecodeError

from .result import Err, Ok, Result


def parse_post_json(request: flask.Request) -> Result[Any, str]:
  """
  Parses a flask post request's body into valid json

  Returns error if request method is not post or if body is invalid json
  """
  if request.method != HTTPMethod.POST:
    return Err(f"Invalid Method! Expected: POST, got: {request.method}")

  # silent=True returns None instead of raising BadRequest
  match request.get_json(silent=True):
    case None:
      return Err("Invalid JSON")
    case json:
      return Ok(json)


def parse_get_json(request: flask.Request) -> Result[dict[str, str], str]:
  """
  Parses a flask get request's url parameters into a json object

  Returns error if request method is not get
  """
  match request.method:
    case HTTPMethod.GET:
      return Ok(request.args.to_dict())
    case method:
      return Err(f"Invalid Method! Expected: GET, got: {method}")


def parse_response_json(response: requests.Response) -> Result[Any, str]:
  """
  Parses a `requests` response into valid json

  Returns error if status code is not 200 or if body is invalid json

  """
  match HTTPStatus(response.status_code):
    case HTTPStatus.OK:
      try:
        return Ok(response.json())
      except JSONDecodeError as e:
        return Err(str(e))
    case code:
      return Err(f"Unexpected status code: {code} ({code.phrase})")
