import functools
import json
import os
import time
import typing as t
import uuid

import redis

from where_it_went.utils.result import Err, Ok, Result


def _default_redis_url() -> str:
  """Get Redis URL from environment or use default."""
  return os.environ.get("REDIS_URL", "redis://redis:6379/0")


@functools.lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
  """Return a cached Redis client (decode_responses=True for JSON strings)."""
  url = _default_redis_url()
  return redis.from_url(url, decode_responses=True)  # type: ignore  # pyright: ignore[reportUnknownMemberType]


# JSON helpers with Result types
def get_json(key: str) -> Result[dict[str, t.Any], str]:
  """Get a JSON value from Redis."""
  try:
    redis_client = get_redis_client()
    val = redis_client.get(key)
    if not val or not isinstance(val, str):
      return Err(f"Key '{key}' not found or not a string")

    try:
      parsed = json.loads(val)
      if not isinstance(parsed, dict):
        return Err(f"Value for key '{key}' is not a JSON object")
      return Ok(parsed)  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    except (json.JSONDecodeError, TypeError) as e:
      return Err(f"Failed to parse JSON for key '{key}': {e}")
  except Exception as e:
    return Err(f"Redis error getting key '{key}': {e}")


def set_json(
  key: str, value: t.Any, expire_seconds: int | None = None
) -> Result[bool, str]:
  """Set a JSON value in Redis with optional expiration."""
  try:
    redis_client = get_redis_client()
    serialized = json.dumps(value)

    if expire_seconds:
      result = redis_client.set(key, serialized, ex=expire_seconds)
    else:
      result = redis_client.set(key, serialized)

    return Ok(bool(result))
  except (TypeError, ValueError) as e:
    return Err(f"Failed to serialize value for key '{key}': {e}")
  except Exception as e:
    return Err(f"Redis error setting key '{key}': {e}")


def delete_key(key: str) -> Result[int, str]:
  """Delete a key from Redis."""
  try:
    redis_client = get_redis_client()
    result = redis_client.delete(key)
    return Ok(int(result))  # pyright: ignore[reportArgumentType]
  except Exception as e:
    return Err(f"Redis error deleting key '{key}': {e}")


# Lock helpers with Result types
def acquire_lock(
  key: str,
  ttl: int = 10,
  wait_timeout: float = 3.0,
  poll_interval: float = 0.05,
) -> Result[str, str]:
  """
  Attempt to acquire a lock. Returns a token string if acquired.
  Using SET NX (Not Exists) with EX for atomic lock acquisition.
  """
  try:
    redis_client = get_redis_client()
    lock_key = f"{key}:lock"
    token = uuid.uuid4().hex
    waited = 0.0

    while waited < wait_timeout:
      result = redis_client.set(lock_key, token, nx=True, ex=ttl)
      if result:
        return Ok(token)

      # Sleep then try again
      time.sleep(poll_interval)
      waited += poll_interval

    return Err(f"Failed to acquire lock '{key}' within {wait_timeout}s")
  except Exception as e:
    return Err(f"Redis error acquiring lock '{key}': {e}")


def release_lock(key: str, token: str) -> Result[dict[str, bool | str], str]:
  """
  Release a lock only if the token matches.
  Uses a Lua script for atomic check-and-delete.
  """
  try:
    redis_client = get_redis_client()
    lock_key = f"{key}:lock"
    script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
      return redis.call("del", KEYS[1])
    else
      return 0
    end
    """

    result = redis_client.eval(script, 1, lock_key, token)
    return Ok({"success": bool(result), "method": "lua_script"})
  except Exception as e:
    # Best-effort fallback
    try:
      redis_client = get_redis_client()
      lock_key = f"{key}:lock"
      current_lock_token = redis_client.get(lock_key)
      if current_lock_token == token:
        result = redis_client.delete(lock_key)
        return Ok({"success": bool(result), "method": "fallback"})
      return Ok({"success": False, "method": "fallback"})
    except Exception as fallback_error:
      return Err(
        f"Redis error releasing lock '{key}': {e}, fallback failed: {fallback_error}"  # noqa: E501
      )


def get_json_simple(key: str) -> dict[str, t.Any] | None:
  """Simple wrapper for get_json that returns None on error."""
  match get_json(key):
    case Ok(value):
      return value
    case Err(_):
      return None


def set_json_simple(
  key: str, value: t.Any, expire_seconds: int | None = None
) -> bool:
  """Simple wrapper for set_json that returns bool."""
  match set_json(key, value, expire_seconds):
    case Ok(success):
      return success
    case Err(_):
      return False
