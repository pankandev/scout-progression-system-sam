import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber

from .. import ModelIndex
from ..model import Operator

interface = ModelIndex('items', 'hash', 'range')


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(interface._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_generate_key():
    with pytest.raises(ValueError):
        interface.generate_key("h")

    composite = interface.generate_key("h", "r")
    assert composite["hash"] == "h"

    with pytest.raises(ValueError):
        interface.generate_key(None, "r")
    interface.generate_key(None, "r", False)


def test_add(ddb_stubber):
    add_item_params = {
        'TableName': 'items',
        'Item': {
            "hash": "value_h",
            "range": "value_r",
            "key_a": "value_a",
            "key_b": "value_b"
        },
        'ReturnValues': 'NONE'
    }
    add_item_response = {}
    ddb_stubber.add_response('put_item', add_item_response, add_item_params)
    item = {
        "key_a": "value_a",
        "key_b": "value_b"
    }
    with pytest.raises(ValueError):
        interface.create("value_h", item)

    interface.create("value_h", item, "value_r")
    ddb_stubber.assert_no_pending_responses()


def test_delete(ddb_stubber):
    delete_item_params = {
        'TableName': 'items',
        'Key': {"hash": "value_h", "range": "value_r"}
    }
    delete_item_response = {}
    ddb_stubber.add_response('delete_item', delete_item_response, delete_item_params)
    with pytest.raises(ValueError):
        interface.delete("value_h")
    interface.delete("value_h", "value_r")

    ddb_stubber.assert_no_pending_responses()


def test_get(ddb_stubber):
    get_item_params = {
        'TableName': 'items',
        'Key': {"hash": "value_h", "range": "value_r"}
    }
    get_item_response = {'Item': {
        'hash': {'S': 'value_h'},
        'range': {'S': 'value_r'},
    }}

    ddb_stubber.add_response('get_item', get_item_response, get_item_params)
    with pytest.raises(ValueError):
        interface.get("value_h")
    result = interface.get("value_h", "value_r")
    assert result.item["hash"] == "value_h"
    assert result.item["range"] == "value_r"
    ddb_stubber.assert_no_pending_responses()


def test_query(ddb_stubber):
    query_params = {
        'TableName': 'items',
        'KeyConditionExpression': Key('hash').eq('value_h') & Key('range').begins_with('val'),
        'Limit': 10
    }
    query_response = {'Items': [
        {
            'hash': {'S': 'value_h'},
            'range': {'S': 'value_r'},
        },
        {
            'hash': {'S': 'value_h_2'},
            'range': {'S': 'value_r'},
        }
    ]}

    ddb_stubber.add_response('query', query_response, query_params)
    result = interface.query(partition_key='value_h', sort_key=(Operator.BEGINS_WITH, 'val'), limit=10)

    for item in result.items:
        assert item["range"] == "value_r"

    assert result.items[0]["hash"] == "value_h"
    assert result.items[1]["hash"] == "value_h_2"

    ddb_stubber.assert_no_pending_responses()


def test_update(ddb_stubber):
    update_params = {
        'TableName': 'items',
        'Key': {
            'hash': 'value_h',
            'range': 'value_r'
        },
        'UpdateExpression': 'SET key_a=:val0, key_b=:val1',
        'ExpressionAttributeNames': {'#attr2': 'key_c'},
        'ExpressionAttributeValues': {'val0': 'value_a', 'val1': 'value_b', 'val2': 'value_c'},
        'ConditionExpression': '#attr2 = :val2'
    }
    update_response = {}

    ddb_stubber.add_response('update_item', update_response, update_params)
    with pytest.raises(ValueError):
        interface.update('value_h', {'key_a': 'value_a', 'key_b': 'value_b'})
    interface.update('value_h', {'key_a': 'value_a', 'key_b': 'value_b'}, 'value_r',
                     condition_equals={'key_c': 'value_c'})

    ddb_stubber.assert_no_pending_responses()
