from http import HTTPMethod, HTTPStatus
from typing import Any, cast

from flask import Flask, Request, Response, jsonify, request
from pydantic import BaseModel, ValidationError

from .utils import result
from .utils.result import Err, Ok, Result

app = Flask(__name__)


def parse_json(request: Request) -> Result[dict[str, Any], str]:
  # silent=True returns None instead of raising BadRequest
  match request.get_json(silent=True):
    case dict(json):  # pyright: ignore[reportUnknownVariableType]
      json = cast(dict[str, Any], json)
      return Ok(json)
    case _:
      return Err("JSON body must be an object")


def decode_model[m: BaseModel](
  model: type[m], json: dict[str, Any]
) -> Result[m, str]:
  try:
    return Ok(model(**json))
  except ValidationError:
    return Err("Validation error, invalid field name or value")


class AddRequest(BaseModel):
  x: int
  y: int


@app.route("/add", methods=[HTTPMethod.POST])
def add() -> tuple[Response, HTTPStatus]:
  add_request_result: Result[AddRequest, str] = result.do(
    Ok(add_request)
    for json in parse_json(request)
    for add_request in decode_model(AddRequest, json)
  )

  match add_request_result:
    case Ok(add_request):
      sum = add_request.x + add_request.y
      return jsonify({"sum": sum}), HTTPStatus.OK
    case Err(e):
      return jsonify({"error": e}), HTTPStatus.BAD_REQUEST
