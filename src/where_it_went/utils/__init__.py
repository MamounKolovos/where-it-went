from functools import reduce
from typing import Any, Callable, overload


@overload
def pipe[a, b](
  value: a,
  a: Callable[[a], b],
) -> b: ...


@overload
def pipe[a, b, c](
  value: a,
  a: Callable[[a], b],
  b: Callable[[b], c],
) -> c: ...


@overload
def pipe[a, b, c, d](
  value: a,
  a: Callable[[a], b],
  b: Callable[[b], c],
  c: Callable[[c], d],
) -> d: ...


@overload
def pipe[a, b, c, d, e](
  value: a,
  a: Callable[[a], b],
  b: Callable[[b], c],
  c: Callable[[c], d],
  d: Callable[[d], e],
) -> e: ...


@overload
def pipe[a, b, c, d, e, f](
  value: a,
  a: Callable[[a], b],
  b: Callable[[b], c],
  c: Callable[[c], d],
  d: Callable[[d], e],
  e: Callable[[e], f],
) -> f: ...


@overload
def pipe[a, b, c, d, e, f, g](
  value: a,
  a: Callable[[a], b],
  b: Callable[[b], c],
  c: Callable[[c], d],
  d: Callable[[d], e],
  e: Callable[[e], f],
  f: Callable[[f], g],
) -> g: ...


@overload
def pipe[a, b, c, d, e, f, g, h](
  value: a,
  a: Callable[[a], b],
  b: Callable[[b], c],
  c: Callable[[c], d],
  d: Callable[[d], e],
  e: Callable[[e], f],
  f: Callable[[f], g],
  g: Callable[[g], h],
) -> h: ...


@overload
def pipe[a, b, c, d, e, f, g, h, i](
  value: a,
  a: Callable[[a], b],
  b: Callable[[b], c],
  c: Callable[[c], d],
  d: Callable[[d], e],
  e: Callable[[e], f],
  f: Callable[[f], g],
  g: Callable[[g], h],
  h: Callable[[h], i],
) -> i: ...


@overload
def pipe[a, b, c, d, e, f, g, h, i, j](
  value: a,
  a: Callable[[a], b],
  b: Callable[[b], c],
  c: Callable[[c], d],
  d: Callable[[d], e],
  e: Callable[[e], f],
  f: Callable[[f], g],
  g: Callable[[g], h],
  h: Callable[[h], i],
  i: Callable[[i], j],
) -> j: ...


def pipe(value: Any, *funcs: Any):  # pyright: ignore[reportInconsistentOverload]
  return reduce(
    lambda val, func: func(val),
    funcs,
    value,
  )
