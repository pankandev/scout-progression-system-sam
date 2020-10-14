import pytest
from botocore.stub import Stubber

from .. import ModelInterface

interface = ModelInterface('items', 'hash')


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(interface._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_generate_key():
    single = interface.generate_key("h")
    assert single["hash"] == "h"

    with pytest.raises(ValueError):
        print(interface.generate_key("h", "r"))


def test_add(ddb_stubber):
    add_item_params = {
        'TableName': 'items',
        'Item': {
            "hash": "value_h",
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
        interface.create("value_h", item, "value_r")

    interface.create("value_h", item)
    ddb_stubber.assert_no_pending_responses()


def test_delete(ddb_stubber):
    delete_item_params = {
        'TableName': 'items',
        'Key': {"hash": "value_h"}
    }
    delete_item_response = {}
    ddb_stubber.add_response('delete_item', delete_item_response, delete_item_params)
    with pytest.raises(ValueError):
        interface.delete("value_h", "value_r")
    interface.delete("value_h")

    ddb_stubber.assert_no_pending_responses()


def test_get(ddb_stubber):
    get_item_params = {
        'TableName': 'items',
        'Key': {"hash": "value_h"}
    }
    get_item_response = {'Item': {
        'hash': {'S': 'value_h'},
        'range': {'S': 'value_r'},
    }}

    ddb_stubber.add_response('get_item', get_item_response, get_item_params)
    with pytest.raises(ValueError):
        interface.get("value_h", "value_r")
    result = interface.get("value_h")
    assert result.item["hash"] == "value_h"
    assert result.item["range"] == "value_r"
    ddb_stubber.assert_no_pending_responses()



def test_query(ddb_stubber):
    query_params = {
        'TableName': 'items',
        'KeyConditions': {
            'hash': {
                'AttributeValueList': ['value_h'],
                'ComparisonOperator': 'EQ'
            }
        },
        'Limit': 10
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
    with pytest.raises(ValueError):
        interface.query('value_h', 'value_r', limit=10)

    result = interface.query('value_h', limit=10)
    for item in result.items:
        assert item["hash"] == "value_h"

    assert result.items[0]["range"] == "value_r"
    assert result.items[1]["range"] == "value_r_2"

    ddb_stubber.assert_no_pending_responses()


def test_update(ddb_stubber):
    update_params = {
        'TableName': 'items',
        'Key': {
            'hash': 'value_h'
        },
        'UpdateExpression': 'SET key_a=:val0, key_b=:val1',
        'ExpressionAttributeValues': {'val0': 'value_a', 'val1': 'value_b'},
    }
    update_response = {}

    ddb_stubber.add_response('update_item', update_response, update_params)
    with pytest.raises(ValueError):
        interface.update('value_h', {'key_a': 'value_a', 'key_b': 'value_b'}, 'value_r')
    interface.update('value_h', {'key_a': 'value_a', 'key_b': 'value_b'})
    ddb_stubber.assert_no_pending_responses()
