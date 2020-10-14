import abc
from typing import List, Dict

from boto3 import dynamodb
from boto3.dynamodb.table import TableResource

import boto3

from .results import QueryResult, GetResult
from .types import DynamoDBKey, DynamoDBTypes

_valid_select_options = ['ALL_ATTRIBUTES', 'ALL_PROJECTED_ATTRIBUTES', 'SPECIFIC_ATTRIBUTES', 'COUNT']


def pass_not_none_arguments(fn, **kwargs):
    args = {}
    for key in kwargs:
        if kwargs[key] is not None:
            args[key] = kwargs[key]
    return fn(**args)


class AbstractModel(abc.ABC):
    __table_name__: str
    __db__: boto3.session.Session.resource
    __keys__: Dict[str, type(DynamoDBTypes)]

    _table: boto3.dynamodb.table = None

    @classmethod
    def get_table(cls):
        if cls._table is None:
            cls._table = cls.__db__.Table(cls.__table_name__)
        return cls._table

    @classmethod
    def scan(cls,
             limit: int = None,
             start_key: DynamoDBKey = None,
             attributes: List[str] = None,
             index: str = None) -> QueryResult:
        """
        List items from a database
        """
        table = cls.get_table()
        result = pass_not_none_arguments(table.scan, Limit=limit, AttributesToGet=attributes, IndexName=index,
                                         ExclusiveStartKey=start_key)
        return QueryResult(result)

    @classmethod
    def query(cls,
              limit: int = None,
              keys: dict = None,
              start_key: DynamoDBKey = None,
              attributes: List[str] = None,
              index: str = None) -> QueryResult:
        """
        List items from a database
        """
        if attributes is not None:
            attributes = ', '.join(attributes)

        key_conditions = None
        if keys is not None:
            key_conditions = {}
            for key, value in keys.items():
                key_conditions[key] = {
                    "AttributeValueList": [value],
                    "ComparisonOperator": "EQ"
                }

        table = cls.get_table()
        result = pass_not_none_arguments(table.query, Limit=limit, ProjectionExpression=attributes, IndexName=index,
                                         ExclusiveStartKey=start_key, KeyConditions=key_conditions)
        return QueryResult(result)

    @classmethod
    def add(cls, item: dict):
        """
        Create an item from the database
        """
        table = cls.get_table()
        return pass_not_none_arguments(table.put_item, Item=item, ReturnValues='NONE')

    @classmethod
    def get(cls, key: DynamoDBKey) -> GetResult:
        """
        Delete an item from the database
        """
        table = cls.get_table()
        result = pass_not_none_arguments(table.get_item, Key=key)
        return GetResult(result)

    @classmethod
    def update(cls, key: DynamoDBKey, item: dict):
        """
        Update an item from the database
        """
        table = cls.get_table()
        return pass_not_none_arguments(table.update_item, Key=key)

    @classmethod
    def delete(cls, key: DynamoDBKey):
        """
        Delete an item from the database
        """
        table = cls.get_table()
        return pass_not_none_arguments(table.delete_item, Key=key)


def create_model(db: boto3.session.Session.resource):
    return type('Model', (AbstractModel,), {'__db__': db})
