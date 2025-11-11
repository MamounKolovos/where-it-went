from where_it_went import config
from where_it_went.app import app, socketio


def main() -> None:
  socketio.run(app, host="0.0.0.0", port=config.get_port(), debug=True)  # pyright: ignore[reportUnknownMemberType]
  return None


if __name__ == "__main__":
  main()
