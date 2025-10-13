from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Generator, Iterator
from typing import Any, NoReturn, cast, final, overload, override


@final
class Ok[T]:
  """
  A value that indicates success
  and which stores arbitrary data for the return value.
  """

  __match_args__ = ("ok_value",)
  __slots__ = ("_value",)

  def __iter__(self) -> Iterator[T]:
    yield self._value

  def __init__(self, value: T) -> None:
    self._value = value

  @override
  def __repr__(self) -> str:
    return "Ok({})".format(repr(self._value))

  @override
  def __eq__(self, other: Any) -> bool:
    return isinstance(other, Ok) and self._value == other._value

  @override
  def __ne__(self, other: Any) -> bool:
    return not (self == other)

  @override
  def __hash__(self) -> int:
    return hash((True, self._value))

  @property
  def ok_value(self) -> T:
    return self._value


class DoError[E](Exception):
  """
  This is used to signal to `do()` that the result is an `Err`,
  which short-circuits the generator and returns that Err.
  Using this exception for control flow in `do()` allows us
  to simulate `and_then()` in the Err case: namely, we don't call `op`,
  we just return `self` (the Err).
  """

  err: Err[E]

  def __init__(self, err: Err[E]) -> None:
    super().__init__(err)
    self.err = err


@final
class Err[E]:
  """
  A value that signifies failure and which stores arbitrary data for the error.
  """

  __match_args__ = ("err_value",)
  __slots__ = ("_value",)

  def __iter__(self) -> Iterator[NoReturn]:
    def _iter() -> Iterator[NoReturn]:
      # Exception will be raised when the iterator is advanced,
      # not when it's created
      raise DoError(self)
      # This yield will never be reached, but is necessary to create a generator
      yield  # pyright: ignore[reportUnreachable]

    return _iter()

  def __init__(self, value: E) -> None:
    self._value = value

  @override
  def __repr__(self) -> str:
    return "Err({})".format(repr(self._value))

  @override
  def __eq__(self, other: Any) -> bool:
    return isinstance(other, Err) and self._value == other._value

  @override
  def __ne__(self, other: Any) -> bool:
    return not (self == other)

  @override
  def __hash__(self) -> int:
    return hash((False, self._value))

  @property
  def err_value(self) -> E:
    return self._value


type Result[T, E] = Ok[T] | Err[E]


class UnwrapError(Exception):
  _result: Result[object, object]

  def __init__(self, result: Result[object, object], message: str) -> None:
    self._result = result
    super().__init__(message)

  @property
  def result(self) -> Result[Any, Any]:
    """
    Returns the original result.
    """
    return self._result


def as_result[**P, R, TBE: BaseException](
  *exceptions: type[TBE],
) -> Callable[[Callable[P, R]], Callable[P, Result[R, TBE]]]:
  """
  Make a decorator to turn a function into one that returns a ``Result``.

  Regular return values are turned into ``Ok(return_value)``. Raised
  exceptions of the specified exception type(s) are turned into ``Err(exc)``.
  """
  if not exceptions or not all(
    inspect.isclass(exception) for exception in exceptions
  ):
    raise TypeError("as_result() requires one or more exception types")

  def decorator(fun: Callable[P, R]) -> Callable[P, Result[R, TBE]]:
    """
    Decorator to turn a function into one that returns a ``Result``.
    """

    @functools.wraps(fun)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Result[R, TBE]:
      try:
        return Ok(fun(*args, **kwargs))
      except exceptions as exc:
        return Err(exc)

    return wrapper

  return decorator


def do[T, E](gen: Generator[Result[T, E], None, None]) -> Result[T, E]:
  """Do notation for Result (syntactic sugar for sequence of `and_then()` calls)


  Usage:

  ```python
  final_result: Result[float, int] = do(
    Ok(len(x) + int(y) + 0.5)
    for x in Ok("hello")
    for y in Ok(True)
  )
  ```
  """
  try:
    return next(gen)
  except DoError as e:  # pyright: ignore[reportUnknownVariableType]
    e = cast(DoError[E], e)
    return e.err
  except TypeError as te:
    raise te


class SpecialUnwrapError(Exception):
  error: object

  def __init__(self, error: object) -> None:
    self.error = error
    super().__init__()


def with_unwrap[**P, a, e](
  func: Callable[P, a | Result[a, e]],
) -> Callable[P, Result[a, e]]:
  @functools.wraps(func)
  def wrapper(*args: P.args, **kwargs: P.kwargs) -> Result[a, e]:
    try:
      ret = func(*args, **kwargs)
      if isinstance(ret, (Ok, Err)):
        return cast(Result[a, e], ret)
      return Ok(ret)

    except SpecialUnwrapError as unwrap_error:
      return Err(cast(e, unwrap_error.error))

  return wrapper


@overload
def unwrap[a, e](result: Result[a, e]) -> a: ...


@overload
def unwrap[a, e]() -> Callable[[Result[a, e]], a]: ...


def do_unwrap[a, e](result: Result[a, e]) -> a:
  match result:
    case Ok(value):
      return value
    case Err(e):
      raise SpecialUnwrapError(e)


def unwrap[a, e](result: Result[a, e] | None = None) -> object:
  match result:
    case None:

      def apply(result: Result[a, e]) -> a:
        return do_unwrap(result)

      return apply
    case result:
      return do_unwrap(result)


@overload
def unwrap_or[a, e](default: a, result: Result[a, e]) -> a: ...


@overload
def unwrap_or[a, e](default: a) -> Callable[[Result[a, e]], a]: ...


def do_unwrap_or[a, e](default: a, result: Result[a, e]) -> a:
  match result:
    case Ok(value):
      return value
    case Err(_):
      return default


def unwrap_or[a, e](default: a, result: Result[a, e] | None = None) -> object:
  match result:
    case None:

      def apply(result: Result[a, e]) -> a:
        return do_unwrap_or(default, result)

      return apply
    case result:
      return do_unwrap_or(default, result)


@overload
def replace_error[a, e, f](error: f, result: Result[a, e]) -> Result[a, f]: ...


@overload
def replace_error[a, e, f](
  error: f,
) -> Callable[[Result[a, e]], Result[a, f]]: ...


def do_replace_error[a, e, f](error: f, result: Result[a, e]) -> Result[a, f]:
  match result:
    case Ok(value):
      return Ok(value)
    case Err(_):
      return Err(error)


def replace_error[a, e, f](
  error: f,  # pyright: ignore[reportInvalidTypeVarUse]
  result: Result[a, e] | None = None,
) -> object:
  match result:
    case None:

      def apply(result: Result[a, e]) -> Result[a, f]:
        return do_replace_error(error, result)

      return apply
    case result:
      return do_replace_error(error, result)


@overload
def map_error[a, e, f](
  func: Callable[[e], f], result: Result[a, e]
) -> Result[a, f]: ...


@overload
def map_error[a, e, f](
  func: Callable[[e], f],
) -> Callable[[Result[a, e]], Result[a, f]]: ...


def do_map_error[a, e, f](
  func: Callable[[e], f], result: Result[a, e]
) -> Result[a, f]:
  match result:
    case Ok(value):
      return Ok(value)
    case Err(error):
      return Err(func(error))


def map_error[a, e, f](
  func: Callable[[e], f], result: Result[a, e] | None = None
) -> object:
  match result:
    case None:

      def apply(result: Result[a, e]) -> Result[a, f]:
        return do_map_error(func, result)

      return apply
    case result:
      return do_map_error(func, result)
