import redis
from flask import Flask
from flask_socketio import SocketIO
from redis import Redis

from where_it_went import routes
from where_it_went.dynamodb_setup import DynamoDBSetup
from where_it_went.socket_setup import SocketSetup

app = Flask(__name__)
app.register_blueprint(routes.bp)
# Use a connection pool to avoid TCP socket race conditions.
# Redis commands are sent over a byte stream, so concurrent writes
# from multiple threads could interleave and corrupt messages.
pool = redis.ConnectionPool(host="redis", port=6379, decode_responses=True)
redis_client = Redis(connection_pool=pool)

# DynamoDB setup
dynamodb_setup = DynamoDBSetup(local=True)


socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")
socketio.on_namespace(SocketSetup("/dev", redis_client, dynamodb_setup))
