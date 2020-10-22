import abc
from typing import List, Dict

from boto3 import dynamodb
from boto3.dynamodb.table import TableResource

import boto3

from .results import QueryResult, GetResult
from .types import DynamoDBKey, DynamoDBTypes

_valid_select_options = ['ALL_ATTRIBUTES', 'ALL_PROJECTED_ATTRIBUTES', 'SPECIFIC_ATTRIBUTES', 'COUNT']


RESERVED_KEYWORDS = ['name']


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

        attr_expression = None
        if attributes is not None:
            attr_expression = {}
            for attr_idx in range(len(attributes)):
                exp = attributes[attr_idx]
                if exp in RESERVED_KEYWORDS:
                    model_exp = f"#model_{exp}"
                    attr_expression[model_exp] = exp
                    exp = model_exp
                attributes[attr_idx] = exp

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
                                         ExclusiveStartKey=start_key, KeyConditions=key_conditions,
                                         ExpressionAttributeNames=attr_expression)
        return QueryResult(result)

    @classmethod
    def add(cls, item: dict):
        """
        Create an item from the database
        """
        table = cls.get_table()
        pass_not_none_arguments(table.put_item, Item=item, ReturnValues='NONE')

    @classmethod
    def get(cls, key: DynamoDBKey, attributes: List[str] = None) -> GetResult:
        """
        Delete an item from the database
        """
        table = cls.get_table()

        attr_expression = None
        if attributes is not None:
            attr_expression = {}
            for attr_idx in range(len(attributes)):
                exp = attributes[attr_idx]
                if exp in RESERVED_KEYWORDS:
                    model_exp = f"#model_{exp}"
                    attr_expression[model_exp] = exp
                    exp = model_exp
                attributes[attr_idx] = exp
            attributes = ', '.join(attributes)

        result = pass_not_none_arguments(table.get_item, Key=key, ProjectionExpression=attributes,
                                         ExpressionAttributeNames=attr_expression)
        return GetResult(result)

    @staticmethod
    def to_code_name(attribute: str, ignore: List[str] = None):
        name = ''.join(map(lambda x: x.capitalize(), attribute.split('-')))
        if ignore is not None:
            while name in ignore:
                name += name
        return name

    @staticmethod
    def to_string_type(t: type):
        if t is int or t is float:
            return 'N'
        if t is str:
            return 'S'
        if t is bin:
            return 'B'
        raise ValueError(f"Unrecognized type: {t}")

    @classmethod
    def update(cls, key: DynamoDBKey, updates: dict):
        """
        Update an item from the database changing only the given attributes
        """
        table = cls.get_table()

        attribute_values = {}

        value_i = 0

        if len(updates) == 0:
            raise ValueError("The updates dictionary must not be empty")

        update_expressions = []
        for item_key, item_value in updates.items():
            value_name = 'val' + str(value_i)
            attribute_values[value_name] = item_value
            update_expressions.append(f"{item_key}=:{value_name}")
            value_i += 1
        expression = "SET " + ', '.join(update_expressions)

        return pass_not_none_arguments(table.update_item,
                                       Key=key,
                                       UpdateExpression=expression,
                                       ExpressionAttributeValues=attribute_values)

    @classmethod
    def delete(cls, key: DynamoDBKey):
        """
        Delete an item from the database
        """
        table = cls.get_table()
        pass_not_none_arguments(table.delete_item, Key=key)


def create_model(db: boto3.session.Session.resource):
    return type('Model', (AbstractModel,), {'__db__': db})
