import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber

from ..db import db


class ItemsModel(db.Model):
    __table_name__ = 'rewards'


@pytest.fixture(scope="function")
def ddb_stubber():
    ddb_stubber = Stubber(ItemsModel.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_add(ddb_stubber):
    item = {"key": "value"}

    add_item_params = {
        'TableName': 'rewards',
        'Item': item,
        'ReturnValues': 'NONE'
    }
    add_item_response = {}
    ddb_stubber.add_response('put_item', add_item_response, add_item_params)

    ItemsModel.add(item)
    ddb_stubber.assert_no_pending_responses()


def test_delete(ddb_stubber):
    key = {"partition": "value_partition", "sort": "value_sort"}

    delete_item_params = {
        'TableName': 'rewards',
        'Key': key
    }
    delete_item_response = {}
    ddb_stubber.add_response('delete_item', delete_item_response, delete_item_params)
    ItemsModel.delete(key)
    ddb_stubber.assert_no_pending_responses()


def test_get(ddb_stubber):
    key = {
        "hash": "value_h",
        "range": "value_r"
    }
    get_item_params = {
        'TableName': 'rewards',
        'Key': key,
        'ExpressionAttributeNames': {'#model_name': 'name'},
        'ProjectionExpression': '#model_name, key'
    }
    get_item_response = {'Item': {
        'hash': {'S': 'value_h'},
        'range': {'S': 'value_r'},
    }}

    ddb_stubber.add_response('get_item', get_item_response, get_item_params)
    result = ItemsModel.get(key, attributes=['name', 'key'])
    assert result.item["hash"] == "value_h"
    assert result.item["range"] == "value_r"
    ddb_stubber.assert_no_pending_responses()


def test_query(ddb_stubber):
    query_params = {
        'TableName': 'rewards',
        'KeyConditionExpression': Key('hash').eq('value_h'),
        'Limit': 10,
        'ProjectionExpression': '#attr_name, #attr_key',
        'ExpressionAttributeNames': {
            '#attr_name': 'name',
            '#attr_key': 'key'
        }
    }
    query_response = {'Items': [
        {
            'hash': {'S': 'value_h'},
            'range': {'S': 'value_r'},
        },
        {
            'hash': {'S': 'value_h'},
            'range': {'S': 'value_r_2'},
        }
    ]}

    ddb_stubber.add_response('query', query_response, query_params)
    result = ItemsModel.query(('hash', 'value_h'), limit=10, attributes=['name', 'key'])
    for item in result.items:
        assert item["hash"] == "value_h"

    assert result.items[0]["range"] == "value_r"
    assert result.items[1]["range"] == "value_r_2"

    ddb_stubber.assert_no_pending_responses()


def test_update(ddb_stubber):
    update_params = {
        'TableName': 'rewards',
        'Key': {
            'hash': 'value_h'
        },
        'UpdateExpression': 'SET #attr_key_a=:val_key_a, #attr_key_b=:val_key_b',
        'ExpressionAttributeNames': {'#attr_key_a': 'key_a', '#attr_key_b': 'key_b'},
        'ExpressionAttributeValues': {':val_key_a': 'value_a', ':val_key_b': 'value_b'},
        'ReturnValues': 'UPDATED_NEW',
    }
    update_response = {}

    ddb_stubber.add_response('update_item', update_response, update_params)
    ItemsModel.update(key={'hash': 'value_h'}, updates={'key_a': 'value_a', 'key_b': 'value_b'})
    ddb_stubber.assert_no_pending_responses()
