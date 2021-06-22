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
    ddb_stubber = Stubber(RewardsService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_create(ddb_stubber):
    response = {}

    now = 1234567890.01234567
    release_id = 290012

    params = {
        'ConditionExpression': 'attribute_not_exists(category) AND attribute_not_exists(#model_release_id)',
        'ExpressionAttributeNames': {'#model_release_id': 'release-id'},
        'Item': {
            'category': 'AVATAR',
            'description': 'An item description',
            'price': 10,
            'release-id': -release_id,
            'rarity': 'RARE'
        },
        'ReturnValues': 'NONE',
        'TableName': 'rewards'
    }

    ddb_stubber.add_response('put_item', response, params)

    event = HTTPEvent({
        "pathParameters": {
            "category": "avatar",
            "release": "3"
        },
        "body": json.dumps({
            'rarity': 'RARE',
            'description': 'An item description',
            'price': 10
        }),
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "abc123",
                    "name": "Name",
                    "family_name": "Family",
                    "cognito:groups": ["Admins"]
                }
            }
        }
    })
    with patch('time.time', lambda: now):
        response = create_item(event)
        assert response.status == 200
    Schema({
        'message': 'Created item',
        'item': {
            'category': 'AVATAR',
            'description': 'An item description',
            'price': 10,
            'rarity': 'RARE',
            'release': 3,
            'id': int
        }
    }).validate(response.body)

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
        'KeyConditionExpression': Key('category').eq('AVATAR') & Key('release-id').lt(400000),
        'TableName': 'rewards',
        'ProjectionExpression': '#attr_category, #attr_description, #attr_release_id, #attr_price, #attr_rarity',
        'ExpressionAttributeNames': {
            '#attr_category': 'category',
            '#attr_description': 'description',
            '#attr_release_id': 'release-id',
            '#attr_price': 'price',
            '#attr_rarity': 'rarity'
        },
    }

    ddb_stubber.add_response('query', response, params)

    event = HTTPEvent({
        "pathParameters": {
            "category": "avatar",
            "release": "3"
        }
    })
    response = list_shop_category(event)
    assert response.status == 200

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
        'TableName': 'rewards',
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
            '#attr_bought_items': 'bought_items',
            '#attr_bought_items_cat301234': 'cat301234',
            '#attr_score_corporality': 'corporality',
            '#attr_score': 'score'
        },
        'ConditionExpression': Attr('score.corporality').gte(20),
        'ExpressionAttributeValues': {':val_bought_items_cat301234': 2,
                                      ':val_score_corporality': -20},
        'UpdateExpression': 'ADD #attr_bought_items.#attr_bought_items_cat301234 :val_bought_items_cat301234, '
                            '#attr_score.#attr_score_corporality :val_score_corporality'
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


def test_get_my_rewards(ddb_stubber: Stubber):
    query_response = {
        'Items': [{
            'user': {'S': 'u-sub'},
            'tag': {'S': 'REWARD::AVATAR'},
            'timestamp': {'N': str(123456)},
            'log': {'S': 'A log'},
            'data': {'M': {'description': {'S': 'An item description'}}},
        }]
    }

    query_params = {
        'TableName': 'logs',
        'KeyConditionExpression': Key('user').eq('u-sub') & Key('tag').begins_with('REWARD::AVATAR'),
        'ScanIndexForward': False
    }
    ddb_stubber.add_response('query', query_response, query_params)
    response = get_my_rewards(HTTPEvent({
        "pathParameters": {
            "category": "avatar",
        },
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "u-sub"
                }
            }
        }
    }))
    assert response.status == 200
    ddb_stubber.assert_no_pending_responses()
