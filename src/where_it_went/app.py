import redis
from flask import Flask
from flask_socketio import SocketIO
from redis import Redis

from where_it_went import routes
from where_it_went.dynamodb_setup import DynamoDBSetup
from where_it_went.service.open_ai import OpenAIService
from where_it_went.service.report_service import ReportService
from where_it_went.socket_setup import SocketSetup

app = Flask(__name__)

# Initialize report service
try:
  report_service = ReportService(OpenAIService())
  routes.report_service = report_service
except Exception as e:
  print(f"[App] Error initializing report service: {e}")
  routes.report_service = None

app.register_blueprint(routes.bp)
# Use a connection pool to avoid TCP socket race conditions.
# Redis commands are sent over a byte stream, so concurrent writes
# from multiple threads could interleave and corrupt messages.
pool = redis.ConnectionPool(host="redis", port=6379, decode_responses=False)
redis_client = Redis(connection_pool=pool)

# DynamoDB setup
dynamodb_setup = DynamoDBSetup(local=True)
# Ensure the NearbyPlaces table exists
_ = dynamodb_setup.load_table("NearbyPlaces")

socketio = SocketIO(
  app,
  async_mode="eventlet",
  cors_allowed_origins="*",
  ping_timeout=120,  # 2 minutes for large radius searches
  ping_interval=25,  # Send ping every 25 seconds
)
socketio.on_namespace(SocketSetup("/dev", redis_client, dynamodb_setup))
