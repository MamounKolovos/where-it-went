import builtins
import functools
import itertools
from collections.abc import Callable
from typing import overload

from where_it_went.utils.result import Err, Ok, Result


@overload
def map[a, b](func: Callable[[a], b], lst: list[a]) -> list[b]: ...
@overload
def map[a, b](func: Callable[[a], b]) -> Callable[[list[a]], list[b]]: ...


def map[a, b](func: Callable[[a], b], lst: list[a] | None = None) -> object:
  match lst:
    case None:

      def apply(lst: list[a]) -> list[b]:
        return [func(element) for element in lst]

      return apply
    case lst:
      return [func(element) for element in lst]


@overload
def flatten[a](lst: list[list[a]]) -> list[a]: ...


@overload
def flatten[a]() -> Callable[[list[list[a]]], list[a]]: ...


def flatten[a](lst: list[list[a]] | None = None) -> object:
  match lst:
    case None:

      def apply(lst: list[list[a]]) -> list[a]:
        return list(itertools.chain.from_iterable(lst))

      return apply
    case lst:
      return list(itertools.chain.from_iterable(lst))


@overload
def fold[a, acc](
  func: Callable[[acc, a], acc], initial: acc, lst: list[a]
) -> acc: ...


@overload
def fold[a, acc](
  func: Callable[[acc, a], acc], initial: acc
) -> Callable[[list[a]], acc]: ...


def fold[a, acc](
  func: Callable[[acc, a], acc], initial: acc, lst: list[a] | None = None
) -> object:
  match lst:
    case None:

      def apply(lst: list[a]) -> acc:
        return functools.reduce(func, lst, initial)

      return apply
    case lst:
      return functools.reduce(func, lst, initial)


def range(start: int, stop: int) -> list[int]:
  return list(builtins.range(start, stop + 1))


@overload
def filter[a](predicate: Callable[[a], bool], lst: list[a]) -> list[a]: ...


@overload
def filter[a](
  predicate: Callable[[a], bool],
) -> Callable[[list[a]], list[a]]: ...


def filter[a](
  predicate: Callable[[a], bool], lst: list[a] | None = None
) -> object:
  match lst:
    case None:

      def apply(lst: list[a]) -> list[a]:
        return list(builtins.filter(predicate, lst))

      return apply
    case lst:
      return list(builtins.filter(predicate, lst))


@overload
def try_map[a, b, e](
  fun: Callable[[a], Result[b, e]], lst: list[a]
) -> Result[list[b], e]: ...


@overload
def try_map[a, b, e](
  fun: Callable[[a], Result[b, e]],
) -> Callable[[list[a]], Result[list[b], e]]: ...


def do_try_map[a, b, e](
  fun: Callable[[a], Result[b, e]], lst: list[a]
) -> Result[list[b], e]:
  acc: list[b] = []
  for item in lst:
    res = fun(item)
    match res:
      case Ok(value):
        acc.append(value)
      case Err(e):
        return Err(e)
  return Ok(acc)


def try_map[a, b, e](
  fun: Callable[[a], Result[b, e]], lst: list[a] | None = None
) -> object:
  match lst:
    case None:

      def apply(lst: list[a]) -> Result[list[b], e]:
        return do_try_map(fun, lst)

      return apply
    case lst:
      return do_try_map(fun, lst)


@overload
def window_by_2[a](lst: list[a]) -> list[tuple[a, a]]: ...


@overload
def window_by_2[a]() -> Callable[[list[tuple[a, a]]], list[tuple[a, a]]]: ...


def window_by_2[a](lst: list[a] | None = None) -> object:
  match lst:
    case None:

      def apply(lst: list[a]) -> list[tuple[a, a]]:
        return list(itertools.pairwise(lst))

      return apply
    case lst:
      return list(itertools.pairwise(lst))


@overload
def sized_chunk[a](count: int, lst: list[a]) -> list[list[a]]: ...


@overload
def sized_chunk[a](count: int) -> Callable[[list[a]], list[list[a]]]: ...


def do_sized_chunk[a](count: int, lst: list[a]) -> list[list[a]]:
  count = 1 if count < 1 else count

  return [list(chunk) for chunk in itertools.batched(lst, count)]


def sized_chunk[a](count: int, lst: list[a] | None = None) -> object:
  match lst:
    case None:

      def apply(lst: list[a]) -> list[list[a]]:
        return do_sized_chunk(count, lst)

      return apply
    case lst:
      return do_sized_chunk(count, lst)


@overload
def group[k, v](to_key: Callable[[v], k], lst: list[v]) -> dict[k, list[v]]: ...


@overload
def group[k, v](
  to_key: Callable[[v], k],
) -> Callable[[list[v]], dict[k, list[v]]]: ...


def do_group[k, v](to_key: Callable[[v], k], lst: list[v]) -> dict[k, list[v]]:
  groups: dict[k, list[v]] = {}
  for element in lst:
    key = to_key(element)
    if key in groups:
      groups[key].append(element)
    else:
      groups[key] = [element]
  return groups


def group[k, v](to_key: Callable[[v], k], lst: list[v] | None = None) -> object:
  match lst:
    case None:

      def apply(lst: list[v]) -> dict[k, list[v]]:
        return do_group(to_key, lst)

      return apply
    case lst:
      return do_group(to_key, lst)


@overload
def argmax[a, b: int | float](func: Callable[[a], b], lst: list[a]) -> a: ...


@overload
def argmax[a, b: int | float](
  func: Callable[[a], b],
) -> Callable[[list[a]], a]: ...


def argmax[a, b: int | float](
  func: Callable[[a], b], lst: list[a] | None = None
) -> object:
  """
  Applies the given function to every element in the list and returns
  the element that produced the highest value
  """
  match lst:
    case None:

      def apply(lst: list[a]) -> a:
        return max(lst, key=func)

      return apply
    case lst:
      return max(lst, key=func)


@overload
def find[a](
  is_desired: Callable[[a], bool], lst: list[a]
) -> Result[a, None]: ...


@overload
def find[a](
  is_desired: Callable[[a], bool],
) -> Callable[[list[a]], Result[a, None]]: ...


def do_find[a](
  is_desired: Callable[[a], bool], lst: list[a]
) -> Result[a, None]:
  for element in lst:
    match is_desired(element):
      case True:
        return Ok(element)
      case False:
        pass

  return Err(None)


def find[a](
  is_desired: Callable[[a], bool], lst: list[a] | None = None
) -> object:
  match lst:
    case None:

      def apply(lst: list[a]) -> Result[a, None]:
        return do_find(is_desired, lst)

      return apply

    case lst:
      return do_find(is_desired, lst)
