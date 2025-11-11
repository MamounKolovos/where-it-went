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

  def __init__(
    self, namespace: str, redis_client: Redis, dynamodb_client: DynamoDBSetup
  ):
    super().__init__(namespace)
    self.namespace = namespace
    self.redis_client = redis_client
    self.dynamodb_client = dynamodb_client

  def on_connect(self):
    print(f"[SocketSetup] Client connected to namespace {self.namespace}")
    # Don't emit 'connect' - it's a reserved Socket.IO event

  def on_disconnect(self):
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
    # Defaulting to GMU's coordinates for now
    latitude = data.get("latitude", 38.832352857203624)
    longitude = data.get("longitude", -77.31284409452543)
    radius = data.get("radius", 1000)
    region = s2helpers.SearchRegion(
      latitude=latitude, longitude=longitude, radius=radius
    )

    @copy_current_request_context
    def stream_update(partial_places: list[Place]):
      emit(
        "places_update", {"places": [p.model_dump() for p in partial_places]}
      )

    try:
      all_places = get_places_in_region(
        self.redis_client, self.dynamodb_client, region, stream_update
      )
      emit("places_complete", {"total": len(all_places)})
    except Exception as e:
      emit("error", {"message": str(e)})
