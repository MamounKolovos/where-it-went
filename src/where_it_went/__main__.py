from where_it_went import config
from where_it_went.app import app


def main() -> None:
  app.run(port=config.get_port(), debug=True)
  return None


if __name__ == "__main__":
  main()
