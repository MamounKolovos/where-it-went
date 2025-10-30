from where_it_went import config
from where_it_went.app import app

# TODO: Uncomment this when we have socketio tested and working
# from where_it_went.app import socketio


def main() -> None:
  app.run(host="0.0.0.0", port=config.get_port(), debug=True)
  # TODO: Uncomment this when we have socketio tested and working
  # and remove the app.run line above
  # socketio.run(app, host="0.0.0.0", port=config.get_port(), debug=True)
  return None


if __name__ == "__main__":
  main()
