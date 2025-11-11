from http import HTTPStatus

import boto3
from mypy_boto3_dynamodb.client import DynamoDBClient
from mypy_boto3_dynamodb.waiter import TableExistsWaiter

from where_it_went.config import get_dynamodb_endpoint
from where_it_went.utils import pipe, result


class DynamoDBSetup:
  session: boto3.Session
  dynamodb_client: DynamoDBClient
  waiter: TableExistsWaiter

  def __init__(self, profile_name: str | None = None, local: bool = False):
    if local:
      endpoint_url = pipe(
        get_dynamodb_endpoint(),
        result.replace_error(
          (
            "Failed to get DynamoDB endpoint",
            HTTPStatus.INTERNAL_SERVER_ERROR,
          )
        ),
        result.unwrap(),
      )
      self.dynamodb_client = boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "dynamodb",
        region_name="us-east-1",
        endpoint_url=endpoint_url,
        aws_access_key_id="dummy",  # DynamoDB Local doesn't validate
        aws_secret_access_key="dummy",
      )
    else:
      # This would be for Production AWS DynamoDB
      self.session = boto3.Session(profile_name=None)
      self.dynamodb_client = self.session.client(  # pyright: ignore[reportUnknownMemberType]
        "dynamodb",
        region_name="us-east-1",
      )
    self.waiter = self.dynamodb_client.get_waiter("table_exists")

  def load_table(self, table_name: str):
    try:
      return self.dynamodb_client.describe_table(TableName=table_name)
    except self.dynamodb_client.exceptions.ResourceNotFoundException:
      nearby_places_table = self.dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=[
          {"AttributeName": "id", "KeyType": "HASH"},
        ],
        AttributeDefinitions=[
          {"AttributeName": "id", "AttributeType": "S"},
        ],
        # TODO: Change to production values or as per testing requirements
        ProvisionedThroughput={
          "ReadCapacityUnits": 50,
          "WriteCapacityUnits": 50,
        },
      )
      self.waiter.wait(TableName=table_name)
      return nearby_places_table
