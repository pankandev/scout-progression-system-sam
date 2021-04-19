import os
from typing import List

from botocore.client import BaseClient

import yaml
import boto3

dir_path = os.path.dirname(os.path.realpath(__file__))


def any_constructor(loader, _, node):
    if isinstance(node, yaml.MappingNode):
        return loader.construct_mapping(node)
    if isinstance(node, yaml.SequenceNode):
        return loader.construct_sequence(node)
    return loader.construct_scalar(node)


def filter_resources_by_type(d: dict, type: str):
    return {res_name: resource for res_name, resource in d['Resources'].items() if resource["Type"] == type}


class KeySchema:
    name: str
    type: str

    def __init__(self, name: str, type_: str):
        self.name = name
        self.type = type_

    @staticmethod
    def from_dict(schema: dict):
        return KeySchema(name=schema["AttributeName"], type_=schema["KeyType"])


class AttributeDefinition:
    name: str
    type: str

    def __init__(self, name: str, type_: str):
        self.name = name
        self.type = type_

    @staticmethod
    def from_dict(schema: dict):
        return AttributeDefinition(name=schema["AttributeName"], type_=schema["AttributeType"])


class Table:
    name: str
    attributes: List[AttributeDefinition]
    keys = List[KeySchema]

    def __init__(self, name: str, attributes: List[AttributeDefinition], keys: List[KeySchema]):
        self.name = name
        self.attributes = attributes
        self.keys = keys

    @staticmethod
    def from_dict(table: dict):
        properties = table["Properties"]
        return Table(name=properties["TableName"],
                     keys=[KeySchema.from_dict(schema) for schema in properties["KeySchema"]],
                     attributes=[AttributeDefinition.from_dict(definition) for definition in
                                 properties["AttributeDefinitions"]])

    def create(self, client: BaseClient):
        print(self.attributes, self.keys)


if __name__ == "__main__":
    db_client = boto3.client('dynamodb', endpoint_url="http://localhost:8000")

    with open(os.path.join(dir_path, '../template.yaml'), 'r') as f:
        yaml.add_multi_constructor('', any_constructor, Loader=yaml.SafeLoader)
        data = yaml.safe_load(f)
    tables = filter_resources_by_type(data, "AWS::DynamoDB::Table").values()
    for table in tables:
        properties = table["Properties"]
        db_client.create_table(**properties)
