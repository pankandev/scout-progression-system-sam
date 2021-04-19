import os
from argparse import ArgumentParser

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


if __name__ == "__main__":
    db_client = boto3.client('dynamodb', endpoint_url="http://localhost:8000")
    db_resource = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")

    db_client.delete_table(TableName="logs")

    with open(os.path.join(dir_path, '../template.yaml'), 'r') as f:
        yaml.add_multi_constructor('', any_constructor, Loader=yaml.SafeLoader)
        data = yaml.safe_load(f)
    tables = [table for table in filter_resources_by_type(data, "AWS::DynamoDB::Table").values() if
              table["Properties"]["TableName"] == "logs"]
    for table in tables:
        properties = table["Properties"]
        db_resource.create_table(**properties)
