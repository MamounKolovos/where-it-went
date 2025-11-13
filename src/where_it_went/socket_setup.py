from flask import copy_current_request_context
from flask_socketio import (
  Namespace,
  emit,  # pyright: ignore[reportUnknownVariableType]
)
from redis import Redis

from where_it_went.dynamodb_setup import DynamoDBSetup
from where_it_went.service.search_places import s2helpers
from where_it_went.service.search_places.search_engine import (
  Place,
  get_places_in_region,
)


class SocketSetup(Namespace):
  redis_client: Redis
  dynamodb_client: DynamoDBSetup
  namespace: str
  active_requests: dict[str, int]  # Track request IDs per client

  def __init__(
    self, namespace: str, redis_client: Redis, dynamodb_client: DynamoDBSetup
  ):
    super().__init__(namespace)
    self.namespace = namespace
    self.redis_client = redis_client
    self.dynamodb_client = dynamodb_client
    self.active_requests = {}

  def on_connect(self):
    print(f"[SocketSetup] Client connected to namespace {self.namespace}")

  def on_disconnect(self):
    from flask import request

    client_id: str = request.sid  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
    # Clean up request tracking for this client
    if client_id in self.active_requests:
      del self.active_requests[client_id]

    print(f"[SocketSetup] Client disconnected from namespace {self.namespace}")
    # Don't emit 'disconnect' - it's a reserved Socket.IO event

  def on_location_update(self, data: dict[str, float]):
    """
    Client sends:
    {
      "latitude": float,
      "longitude": float,
      "radius": float
    }
    """
    from flask import request

    # Get client session ID and increment request counter
    client_id: str = request.sid  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType, reportAttributeAccessIssue]
    request_id = self.active_requests.get(client_id, 0) + 1  # pyright: ignore[reportUnknownArgumentType]
    self.active_requests[client_id] = request_id

    print(
      f"[SocketSetup] Processing request {request_id} for client {client_id}"
    )

    # Defaulting to GMU's coordinates for now
    latitude = data.get("latitude", 38.832352857203624)
    longitude = data.get("longitude", -77.31284409452543)
    radius = data.get("radius", 1000)
    region = s2helpers.SearchRegion(
      latitude=latitude, longitude=longitude, radius=radius
    )

    def should_cancel() -> bool:
      return self.active_requests.get(client_id) != request_id  # pyright: ignore[reportUnknownArgumentType]

    @copy_current_request_context
    def stream_update(partial_places: list[Place]):
      import eventlet  # pyright: ignore[reportMissingTypeStubs]

      # Check if this request is still active
      if should_cancel():
        return

      emit(
        "places_update", {"places": [p.model_dump() for p in partial_places]}
      )
      # Delay to prevent Socket.IO from batching multiple emits
      eventlet.sleep(0.01)  # type: ignore  # pyright: ignore[reportArgumentType]

    try:
      # Check if request is still active before processing
      if should_cancel():
        print(f"[SocketSetup] Request {request_id} cancelled before processing")
        return

      all_places = get_places_in_region(
        self.redis_client,
        self.dynamodb_client,
        region,
        stream_update,
        should_cancel,
      )

      # Only emit completion if this is still the active request
      if not should_cancel():
        emit("places_complete", {"total": len(all_places)})
    except Exception as e:
      if not should_cancel():
        emit("error", {"message": str(e)})
