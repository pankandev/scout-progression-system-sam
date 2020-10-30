import abc
from typing import List, Dict, Any

from boto3 import dynamodb
from boto3.dynamodb.table import TableResource

import boto3

from .results import QueryResult, GetResult
from .types import DynamoDBKey, DynamoDBTypes

_valid_select_options = ['ALL_ATTRIBUTES', 'ALL_PROJECTED_ATTRIBUTES', 'SPECIFIC_ATTRIBUTES', 'COUNT']

RESERVED_KEYWORDS = ['name', 'unit', 'sub', 'user']


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

    @staticmethod
    def replace_keyword_attributes(attributes: List[str]):
        attr_expression = {}
        for attr_idx in range(len(attributes)):
            exp = attributes[attr_idx]
            if exp in RESERVED_KEYWORDS or '-' in exp:
                model_exp = f"#model_{exp}".replace('-', '_')
                attr_expression[model_exp] = exp
                exp = model_exp
            attributes[attr_idx] = exp
        if len(attr_expression) == 0:
            attr_expression = None
        return attr_expression

    @staticmethod
    def attributes_to_projection_and_expression(attributes: List[str]):
        attr_expression = AbstractModel.replace_keyword_attributes(attributes)
        attributes = ', '.join(attributes)
        return attr_expression, attributes

    @classmethod
    def query(cls,
              limit: int = None,
              keys: dict = None,
              start_key: DynamoDBKey = None,
              attributes: List[str] = None,
              index: str = None,
              begins_with: dict = None
              ) -> QueryResult:
        """
        List items from a database
        """

        attr_expression = {}
        if attributes is not None:
            attr_expression, attributes = cls.attributes_to_projection_and_expression(attributes)

        attr_values = {}

        val_i = 0
        and_conditions = list()
        keys_exp = {}
        if keys is not None:
            keys_ = list(keys.keys())
            xp = AbstractModel.replace_keyword_attributes(keys_)
            keys_exp = {**({} if xp is None else xp), **keys_exp}
            for key in keys_:
                value = keys[keys_exp.get(key, key)]
                val_name = ':val_' + str(val_i)
                attr_values[val_name] = {'S': value}
                and_conditions.append(f'{key} = {val_name}')
                val_i += 1
        if begins_with is not None:
            keys_ = list(begins_with.keys())
            xp = AbstractModel.replace_keyword_attributes(keys_)
            keys_exp = {**({} if xp is None else xp), **keys_exp}
            for key in keys_:
                value = begins_with[keys_exp.get(key, key)]
                val_name = ':val_' + str(val_i)
                attr_values[val_name] = {'S': value}
                and_conditions.append(f'begins_with({key}, {val_name})')
                val_i += 1
        name_expressions = {**attr_expression, **keys_exp}
        if len(name_expressions) == 0:
            name_expressions = None

        key_conditions = ' AND '.join(and_conditions) if and_conditions is not None else None
        table = cls.get_table()
        result = pass_not_none_arguments(table.query, Limit=limit, ProjectionExpression=attributes, IndexName=index,
                                         ExclusiveStartKey=start_key, KeyConditionExpression=key_conditions,
                                         ExpressionAttributeNames=name_expressions,
                                         ExpressionAttributeValues=attr_values)
        return QueryResult(result)

    @classmethod
    def add(cls, item: dict, raise_if_attributes_exist: List[str] = None, conditions: List[str] = None,
            raise_attribute_equals: dict = None):
        """
        Create an item from the database
        """
        # [f'#model_sub=:val_sub'], attribute_values = {":val_sub": {"S": authorizer.sub}}
        table = cls.get_table()

        exp = None
        if raise_if_attributes_exist is not None:
            exp = cls.replace_keyword_attributes(raise_if_attributes_exist)
            conditions = list() if conditions is None else conditions
            for attr in raise_if_attributes_exist:
                conditions.append(f'attribute_not_exists({attr})')
            conditions = [' AND '.join(conditions)]

        attribute_values = None
        if raise_attribute_equals is not None:
            attribute_values = {}
            if exp is None:
                exp = {}
            attrs = list(raise_attribute_equals.keys())
            exp = {**exp, **cls.replace_keyword_attributes(attrs)}
            and_conditions = list()
            for attr in attrs:
                val_name = ':val_' + exp[attr]
                val = raise_attribute_equals[exp[attr]]
                attribute_values[val_name] = {'S': val}
                and_conditions.append(f'NOT {attr} = {val_name}')
            conditions = list() if conditions is None else conditions
            conditions.append(' AND '.join(and_conditions))

        condition = ' AND '.join(conditions) if conditions is not None else None
        pass_not_none_arguments(table.put_item, Item=item, ReturnValues='NONE', ConditionExpression=condition,
                                ExpressionAttributeNames=exp, ExpressionAttributeValues=attribute_values)

    @classmethod
    def get(cls, key: DynamoDBKey, attributes: List[str] = None) -> GetResult:
        """
        Delete an item from the database
        """
        table = cls.get_table()

        attr_expression = None
        if attributes is not None:
            attr_expression, attributes = cls.attributes_to_projection_and_expression(attributes)

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
    def update(cls, key: DynamoDBKey, updates: dict = None, append_to: Dict[str, Any] = None,
               condition_equals: Dict[str, Any] = None, add_to: Dict[str, int] = None):
        """
        Update an item from the database changing only the given attributes
        """
        table = cls.get_table()

        attribute_values = {}

        value_i = 0

        if updates is None:
            updates = {}

        if append_to is None:
            append_to = {}

        if add_to is None:
            add_to = {}

        if len(updates) == 0 and len(append_to) == 0:
            raise ValueError("The updates or append_to dictionary must not be empty")

        update_expressions = []
        for item_key, item_value in updates.items():
            value_name = 'val' + str(value_i)
            attribute_values[value_name] = item_value
            update_expressions.append(f"{item_key}=:{value_name}")
            value_i += 1
        for item_key, item_value in append_to.items():
            value_name = 'val' + str(value_i)
            attribute_values[value_name] = item_value
            update_expressions.append(f"{item_key}=list_append({item_key}, :{value_name})")
            value_i += 1
        if len(update_expressions) > 0:
            expression = "SET " + ', '.join(update_expressions)
        else:
            expression = None

        add_expressions = []
        for item_key, amount in add_to.items():
            value_name = 'val' + str(value_i)
            attribute_values[value_name] = item_value
            add_expressions.append(f"{item_key}=list_append({item_key}, :{value_name})")
            value_i += 1
        if len(add_expressions) > 0:
            expression = ("" if expression is None else expression + " ") + "ADD " + ', '.join(add_expressions)

        conditions = list()

        attribute_names = None
        if condition_equals is not None:
            attribute_names = dict()
            for attr_key, attr_value in condition_equals.items():
                key_name = '#attr' + str(value_i)
                attribute_names[key_name] = attr_key

                value_name = 'val' + str(value_i)
                attribute_values[value_name] = attr_value
                conditions.append(f"{key_name} = :{value_name}")
                value_i += 1

        if len(conditions) == 0:
            condition_exp = None
        else:
            condition_exp = ' AND '.join(conditions)
        return pass_not_none_arguments(table.update_item,
                                       Key=key,
                                       UpdateExpression=expression,
                                       ExpressionAttributeNames=attribute_names,
                                       ExpressionAttributeValues=attribute_values,
                                       ConditionExpression=condition_exp
                                       )

    @classmethod
    def delete(cls, key: DynamoDBKey):
        """
        Delete an item from the database
        """
        table = cls.get_table()
        pass_not_none_arguments(table.delete_item, Key=key)


def create_model(db: boto3.session.Session.resource):
    return type('Model', (AbstractModel,), {'__db__': db})
