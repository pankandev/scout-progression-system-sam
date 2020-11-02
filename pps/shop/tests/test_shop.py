import json
from decimal import Decimal
from unittest.mock import patch

import pytest
from boto3.dynamodb.conditions import Key, Attr
from botocore.stub import Stubber

from ..app import *


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(ShopService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_create(ddb_stubber):
    response = {}

    now = 1234567890.01234567
    release_id = 390012

    params = {
        'ConditionExpression': 'attribute_not_exists(category) AND attribute_not_exists(#model_release_id)',
        'ExpressionAttributeNames': {'#model_release_id': 'release-id'},
        'Item': {
            'category': 'cat',
            'description': 'An item description',
            'name': 'An Item',
            'price': 10,
            'release-id': Decimal(release_id)
        },
        'ReturnValues': 'NONE',
        'TableName': 'items'
    }

    ddb_stubber.add_response('put_item', response, params)

    event = HTTPEvent({
        "pathParameters": {
            "category": "cat",
            "release": "3"
        },
        "body": json.dumps({
            'name': 'An Item',
            'description': 'An item description',
            'price': 10
        })
    })
    with patch('time.time', lambda: now):
        create_item(event)

    ddb_stubber.assert_no_pending_responses()


def test_query(ddb_stubber):
    response = {}

    params = {
        'KeyConditionExpression': Key('category').eq('cat') & Key('release-id').lt(400000),
        'TableName': 'items',
        'ProjectionExpression': '#attr_name, #attr_category, #attr_description',
        'ExpressionAttributeNames': {
            '#attr_category': 'category',
            '#attr_description': 'description',
            '#attr_name': 'name'
        },
    }

    ddb_stubber.add_response('query', response, params)

    event = HTTPEvent({
        "pathParameters": {
            "category": "cat",
            "release": "3"
        }
    })
    list_shop_category(event)

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
        'Key': {'category': 'cat', 'release-id': 301234},
        'ProjectionExpression': '#model_name, category, description, #model_release_id, price',
        'ExpressionAttributeNames': {
            '#model_name': 'name',
            '#model_release_id': 'release-id'
        },
    }

    ddb_stubber.add_response('get_item', response, params)
    event = HTTPEvent({
        "pathParameters": {
            "category": "cat",
            "release": "3",
            "id": "1234"
        }
    })
    get_item(event)

    ddb_stubber.assert_no_pending_responses()


def test_query(ddb_stubber):
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
        'KeyConditionExpression': Key('category').eq('cat') & Key('release-id').lt(400000),
        'TableName': 'items',
        'ProjectionExpression': '#attr_name, #attr_category, #attr_description, #attr_release_id, #attr_price',
        'ExpressionAttributeNames': {
            '#attr_category': 'category',
            '#attr_description': 'description',
            '#attr_name': 'name',
            '#attr_release_id': 'release-id',
            '#attr_price': 'price'
        },
    }

    ddb_stubber.add_response('query', response, params)

    event = HTTPEvent({
        "pathParameters": {
            "category": "cat",
            "release": "3"
        }
    })
    list_shop_category(event)

    ddb_stubber.assert_no_pending_responses()


def test_buy(ddb_stubber: Stubber):
    get_response = {
        'Item': {
            'category': {'S': 'cat'},
            'name': {'S': 'An item'},
            'description': {'S': 'An item description'},
            'price': {'N': '10'},
            'release-id': {'N': '301234'}
        }
    }

    get_params = {
        'TableName': 'items',
        'Key': {'category': 'cat', 'release-id': 301234},
        'ProjectionExpression': '#model_name, category, description, #model_release_id, price',
        'ExpressionAttributeNames': {
            '#model_name': 'name',
            '#model_release_id': 'release-id'
        },
    }

    update_response = {
        "Attributes": {
            "score.corporality": {'N': '-20'},
            "bought_items.shirts127190": {'N': '2'}
        }
    }

    update_params = {
        'TableName': 'beneficiaries',
        'Key': {'user': 'u-sub'},
        'ReturnValues': 'UPDATED_NEW',
        'ExpressionAttributeNames': {
            '#attr_bought_items_cat301234': 'bought_items.cat301234',
            '#attr_score_corporality': 'score.corporality'
        },
        'ConditionExpression': Attr('score.corporality').gte(20),
        'ExpressionAttributeValues': {':val_bought_items_cat301234': 2,
                                      ':val_score_corporality': -20},
        'UpdateExpression': 'ADD #attr_bought_items_cat301234 :val_bought_items_cat301234, '
                            '#attr_score_corporality :val_score_corporality'
    }

    ddb_stubber.add_response('get_item', get_response, get_params)
    ddb_stubber.add_response('update_item', update_response, update_params)
    event = HTTPEvent({
        "pathParameters": {
            "category": "cat",
            "release": "3",
            "id": "1234",
            "area": "corporality"
        },
        "body": json.dumps({
            'amount': 2
        }),
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "u-sub"
                }
            }
        }
    })
    buy_item(event)

    ddb_stubber.assert_no_pending_responses()
