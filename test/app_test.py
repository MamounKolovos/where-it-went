from collections.abc import Generator
from http import HTTPStatus

import pytest
from flask.testing import FlaskClient

from where_it_went.app import app

if __name__ == "__main__":
  _ = pytest.main()


@pytest.fixture
def client() -> Generator[FlaskClient, None, None]:
  """
  Provides test client which simulates requests
  without actually running a live server
  """
  with app.test_client() as client:
    yield client


def add_1_test(client: FlaskClient) -> None:
  response = client.post("/add", json={"x": 5, "y": 3})
  assert response.status_code == HTTPStatus.OK
  assert response.get_json() == {"sum": 8}


def add_2_test(client: FlaskClient) -> None:
  response = client.post("/add", json="x")
  assert (
    response.status_code == HTTPStatus.BAD_REQUEST
    and "error" in response.get_json()
  )


def add_3_test(client: FlaskClient) -> None:
  response = client.post("/add", json={"_x": 5, "y": 3})
  assert (
    response.status_code == HTTPStatus.BAD_REQUEST
    and "error" in response.get_json()
  )


def add_4_test(client: FlaskClient) -> None:
  response = client.post("/add", json={"_x": 5, "_y": 3})
  assert (
    response.status_code == HTTPStatus.BAD_REQUEST
    and "error" in response.get_json()
  )
