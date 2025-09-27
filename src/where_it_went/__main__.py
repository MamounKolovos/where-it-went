import os

from .app import app


def get_port() -> int:
  """
  Retrieve the port the app listens on

  Defaults to 5000 if not present or if not a valid integer
  """
  match os.getenv("PORT"):
    case None:
      return 5000
    case port:
      try:
        return int(port)
      except Exception:
        return 5000


def main() -> None:
  app.run(port=get_port(), debug=True)
  return None


if __name__ == "__main__":
  main()
