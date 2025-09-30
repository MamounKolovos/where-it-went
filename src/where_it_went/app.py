from http import HTTPMethod, HTTPStatus

import flask
from flask import Flask, jsonify, request
from pydantic import BaseModel

from .service.search_nearby import search_nearby_blueprint
from .utils import result
from .utils.decoding import decode_model
from .utils.http import parse_post_json
from .utils.result import Err, Ok, Result

app = Flask(__name__)
app.register_blueprint(search_nearby_blueprint)


class AddRequest(BaseModel):
  x: int
  y: int


@app.route("/add", methods=[HTTPMethod.POST])
def add() -> tuple[flask.Response, HTTPStatus]:
  add_request_result: Result[AddRequest, str] = result.do(
    Ok(add_request)
    for json in parse_post_json(request)
    for add_request in decode_model(AddRequest, json)
  )

  match add_request_result:
    case Ok(add_request):
      sum = add_request.x + add_request.y
      return jsonify({"sum": sum}), HTTPStatus.OK
    case Err(e):
      return jsonify({"error": e}), HTTPStatus.BAD_REQUEST
