from decimal import Decimal
from unittest.mock import patch

import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber

from core.services.shop import ShopService


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(ShopService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_create(ddb_stubber: Stubber):
    response = {}

    now = 1234567890.01234567
    release_id = 390012

    params = {
        'ConditionExpression': 'attribute_not_exists(category) AND attribute_not_exists(#model_release_id)',
        'ExpressionAttributeNames': {'#model_release_id': 'release-id'},
        'Item': {
            'category': 'category',
            'description': 'An item description',
            'name': 'item',
            'price': 10,
            'release-id': release_id
        },
        'ReturnValues': 'NONE',
        'TableName': 'items'
    }

    ddb_stubber.add_response('put_item', response, params)

    with patch('time.time', lambda: now):
        ShopService.create("item", "An item description", 10, "category", 3)

    ddb_stubber.assert_no_pending_responses()


def test_query(ddb_stubber: Stubber):
    response = {
        'Items': [{
            'name': {'S': 'An item'},
            'description': {'S': 'An item description'},
            'release-id': {'N': '312345'},
            'category': {'S': 'category'},
        }],
        'Count': 0
    }

    params = {
        'KeyConditionExpression': Key('category').eq('category') & Key('release-id').lt(400000),
        'TableName': 'items',
        'ProjectionExpression': '#attr_name, #attr_category, #attr_description, #attr_release_id',
        'ExpressionAttributeNames': {
            '#attr_category': 'category',
            '#attr_description': 'description',
            '#attr_name': 'name',
            '#attr_release_id': 'release-id'
        },
    }

    ddb_stubber.add_response('query', response, params)
    result = ShopService.query("category", 3)
    assert result.items[0]['release'] == 3
    assert result.items[0]['id'] == 12345

    ddb_stubber.assert_no_pending_responses()


def test_get(ddb_stubber: Stubber):
    response = {
        'Item': {
            'name': {'S': 'An item'},
            'description': {'S': 'An item description'},
            'release-id': {'N': '312345'},
            'category': {'S': 'category'},
        }
    }

    params = {
        'TableName': 'items',
        'Key': {'category': 'category', 'release-id': 312345},
        'ProjectionExpression': '#model_name, category, description, #model_release_id',
        'ExpressionAttributeNames': {
            '#model_name': 'name',
            '#model_release_id': 'release-id'
        },
    }

    ddb_stubber.add_response('get_item', response, params)
    ShopService.get("category", 3, 12345)

    ddb_stubber.assert_no_pending_responses()
