import abc
import enum
from typing import List, Dict, Any, Tuple, Union

from boto3 import dynamodb
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.table import TableResource

import boto3

from .results import QueryResult, GetResult
from .types import DynamoDBKey, DynamoDBTypes
from ..exceptions.invalid import InvalidException

_valid_select_options = ['ALL_ATTRIBUTES', 'ALL_PROJECTED_ATTRIBUTES', 'SPECIFIC_ATTRIBUTES', 'COUNT']

RESERVED_KEYWORDS = ['name', 'unit', 'sub', 'user', 'group']


def pass_not_none_arguments(fn, **kwargs):
    args = {}
    for key in kwargs:
        if kwargs[key] is not None:
            args[key] = kwargs[key]
    return fn(**args)


class UpdateReturnValues(enum.Enum):
    NONE = 0
    ALL_OLD = 1
    UPDATED_OLD = 2
    ALL_NEW = 3
    UPDATED_NEW = 4

    @staticmethod
    def to_str(value):
        if value == UpdateReturnValues.NONE:
            return "NONE"
        elif value == UpdateReturnValues.ALL_OLD:
            return "ALL_OLD"
        elif value == UpdateReturnValues.UPDATED_OLD:
            return "UPDATED_OLD"
        elif value == UpdateReturnValues.ALL_NEW:
            return "ALL_NEW"
        elif value == UpdateReturnValues.UPDATED_NEW:
            return "UPDATED_NEW"
        raise ValueError(f"Unknown UpdateReturnValues: {value}")


class Operator(enum.Enum):
    EQ = 0
    BEGINS_WITH = 1
    LESS_THAN = 2
    GREATER_THAN = 3
    GREATER_THAN_OR_EQUAL = 4
    LOWER_THAN_OR_EQUAL = 5
    BETWEEN = 6

    @staticmethod
    def to_expression(key_name, op, value, value2=None):
        exp = Key(key_name)
        if op == Operator.EQ:
            exp = exp.eq(value)
        elif op == Operator.BEGINS_WITH:
            exp = exp.begins_with(value)
        elif op == Operator.LESS_THAN:
            exp = exp.lt(value)
        elif op == Operator.GREATER_THAN:
            exp = exp.gt(value)
        elif op == Operator.GREATER_THAN_OR_EQUAL:
            exp = exp.gte(value)
        elif op == Operator.LOWER_THAN_OR_EQUAL:
            exp = exp.lte(value)
        elif op == Operator.BETWEEN:
            if value2 is None:
                raise Exception('Undefined second value for BETWEEN sort key operator')
            exp = exp.between(value, value2)
        else:
            raise ValueError(f"Unknown operator {str(op)}")
        return exp


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

    @staticmethod
    def clean_for_exp(text: str):
        return text.replace('-', '_').replace('.', '_')

    @staticmethod
    def add_to_attribute_names(attribute: str, attribute_names: dict, prefix: str = None) -> str:
        dot_splitted = attribute.split('.')
        if len(dot_splitted) > 1:
            exp = []
            for attr in dot_splitted:
                pref = '_'.join(exp).replace('#attr_', '')
                exp.append(AbstractModel.add_to_attribute_names(attr, attribute_names, pref))
            name_exp = '.'.join(exp)
        else:
            name = (prefix + '_' if prefix else '') + attribute
            name_exp = AbstractModel.clean_for_exp(f"#attr_{name}")
            attribute_names[name_exp] = attribute
        return name_exp

    @staticmethod
    def value_to_value_expression(value: Union[str, int, float, dict, bool]):
        types = {
            str: 'S',
            int: 'N',
            float: 'N',
            dict: 'M',
            bool: 'BOOL',
            list: 'L',
            type(None): 'NULL'
        }
        value_type = types[type(value)]
        if value_type == 'NULL':
            value = True

        return {value_type: value}

    @staticmethod
    def add_to_attribute_values(value: Any, attribute_values: dict, attribute: str) -> str:
        name_exp = f":val_{attribute}".replace('-', '_').replace('.', '_')
        attribute_values[name_exp] = value
        return name_exp

    @classmethod
    def query(cls,
              partition_key: Tuple[str, Any],
              sort_key: Union[Tuple[str, Operator, Any], List[Tuple[str, Operator, Any]]] = None,
              limit: int = None,
              start_key: DynamoDBKey = None,
              attributes: List[str] = None,
              index: str = None,
              ) -> QueryResult:
        """
        List items from a database
        """

        if sort_key is None:
            sort_key = []
        if isinstance(sort_key, tuple):
            sort_key = [sort_key]

        attr_names = {}

        projection = None
        if attributes is not None:
            projection = ', '.join([cls.add_to_attribute_names(attr, attr_names) for attr in attributes])

        hash_name, hash_value = partition_key
        key_conditions = Operator.to_expression(hash_name, Operator.EQ, hash_value)

        if len(sort_key) > 0:
            for key in sort_key:
                if len(key) == 3:
                    sort_name, sort_op, sort_value = key
                    sort_value_2 = None
                elif len(key) == 4:
                    sort_name, sort_op, sort_value, sort_value_2 = key
                else:
                    raise Exception(f'Sort key operator have {len(key)} instead of 3 or 4')
                key_conditions = key_conditions & Operator.to_expression(sort_name, sort_op, sort_value, sort_value_2)
        if len(attr_names) == 0:
            attr_names = None

        table = cls.get_table()
        result = pass_not_none_arguments(table.query, Limit=limit, ProjectionExpression=projection, IndexName=index,
                                         ExclusiveStartKey=start_key, KeyConditionExpression=key_conditions,
                                         ExpressionAttributeNames=attr_names)
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
        return item

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
               condition_equals: Dict[str, Any] = None, add_to: Dict[str, int] = None, conditions=None,
               return_values: UpdateReturnValues = UpdateReturnValues.UPDATED_NEW):
        """
        Update an item from the database changing only the given attributes
        """
        table = cls.get_table()

        if updates is None:
            updates = {}

        if append_to is None:
            append_to = {}

        if add_to is None:
            add_to = {}

        if len(updates) == 0 and len(append_to) == 0 and len(add_to) == 0:
            raise ValueError("The updates, append_to and add_to dictionaries must not be empty at the same time")

        attr_names = {}
        attr_values = {}
        update_expressions = []
        for item_key, item_value in updates.items():
            item_key_ = cls.add_to_attribute_names(item_key, attr_names)
            item_value_ = cls.add_to_attribute_values(item_value, attr_values, item_key)
            update_expressions.append(f"{item_key_}={item_value_}")
        for item_key, item_value in append_to.items():
            item_key_ = cls.add_to_attribute_names(item_key, attr_names)
            item_value_ = cls.add_to_attribute_values(item_value, attr_values, item_key)
            update_expressions.append(f"{item_key_}=list_append({item_key_}, {item_value_})")
        if len(update_expressions) > 0:
            expression = "SET " + ', '.join(update_expressions)
        else:
            expression = None

        add_expressions = []
        for item_key, amount in add_to.items():
            item_key_ = cls.add_to_attribute_names(item_key, attr_names)
            item_value_ = cls.add_to_attribute_values(amount, attr_values, item_key)
            add_expressions.append(f"{item_key_} {item_value_}")
        if len(add_expressions) > 0:
            expression = ("" if expression is None else expression + " ") + "ADD " + ', '.join(add_expressions)

        eq_conditions = list()

        if condition_equals is not None:
            for item_key, item_value in condition_equals.items():
                item_key_ = cls.add_to_attribute_names(item_key, attr_names)
                item_value_ = cls.add_to_attribute_values(item_value, attr_values, item_key + '_condition')

                eq_conditions.append(f"{item_key_} = {item_value_}")

        if len(eq_conditions) == 0:
            condition_exp = None
        else:
            condition_exp = ' AND '.join(eq_conditions)

        if len(attr_names) == 0:
            attr_names = None
        if len(attr_values) == 0:
            attr_values = None

        return pass_not_none_arguments(table.update_item,
                                       Key=key,
                                       UpdateExpression=expression,
                                       ExpressionAttributeNames=attr_names,
                                       ExpressionAttributeValues=attr_values,
                                       ConditionExpression=conditions if conditions is not None else condition_exp,
                                       ReturnValues=UpdateReturnValues.to_str(return_values),
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
