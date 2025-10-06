from typing import Any

from pydantic import BaseModel, ValidationError

from where_it_went.utils.result import Err, Ok, Result


def decode_model[m: BaseModel](model: type[m], json: Any) -> Result[m, str]:
  match json:
    case dict(data):  # pyright: ignore[reportUnknownVariableType]
      try:
        return Ok(model(**data))
      except ValidationError as e:
        return Err(str(e))
    case _:
      return Err("Only json objects can be decoded into a pydantic model")
