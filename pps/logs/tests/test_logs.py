import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber
from freezegun import freeze_time
from schema import Schema

from core.aws.event import Authorizer
from core.services.logs import LogsService
from core.services.tasks import Task
from ..app import *


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(LogsService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_query(ddb_stubber: Stubber):
    ddb_stubber.add_response('query', {
        'Items': [
            {
                'user': {'S': 'u-sub'},
                'tag': {'S': 'A-TAG'},
                'timestamp': {'N': str(123456)},
                'log': {'S': 'A log!'}
            },
            {
                'user': {'S': 'u-sub'},
                'tag': {'S': 'A-TAG'},
                'timestamp': {'N': str(123457)},
                'log': {'S': 'A log!'}
            }
        ]
    }, {
                                 'TableName': 'logs',
                                 'KeyConditionExpression': Key('user').eq('u-sub') & Key('tag').begins_with('A-TAG'),
                                 'Limit': 25,
                                 'ScanIndexForward': False
                             })
    response = query_logs(HTTPEvent({
        "pathParameters": {
            "sub": "u-sub",
            "tag": "A-TAG"
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
    Schema({
        'items': [
            {
                'user': 'u-sub',
                'tag': 'A-TAG',
                'timestamp': 123456,
                'log': 'A log!'
            },
            {
                'user': 'u-sub',
                'tag': 'A-TAG',
                'timestamp': 123457,
                'log': 'A log!'
            }
        ],
        'count': 2,
        'last_key': None
    }).validate(response.body)

    ddb_stubber.assert_no_pending_responses()


@freeze_time('2020-01-01')
def test_create(ddb_stubber: Stubber):
    ddb_stubber.add_response('query', {
        'Items': [
            {
                'user': {'S': 'u-sub'},
                'tag': {'S': 'PROGRESS::PUBERTY::CORPORALITY::1::' + str(1577836800000 - 24 * 60 * 60 * 1000 - 1)},
                'timestamp': {'N': str(1577836800000 - 24 * 60 * 60 * 1000 - 1)},
                'log': {'S': 'A log!'}
            }
        ]
    }, {'TableName': 'logs',
        'ScanIndexForward': False,
        'Limit': 1,
        'KeyConditionExpression': Key('user').eq('u-sub') & Key('tag').begins_with(
            'PROGRESS::PUBERTY::CORPORALITY::1::')
        })
    ddb_stubber.add_response('update_item', {
        'Attributes': {'generated_token_last': {'S': '0'}}
    }, {'ExpressionAttributeNames': {'#attr_generated_token_last': 'generated_token_last'},
        'ExpressionAttributeValues': {':val_generated_token_last': 1},
        'Key': {'user': 'u-sub'},
        'ReturnValues': 'UPDATED_NEW',
        'TableName': 'beneficiaries',
        'UpdateExpression': 'ADD #attr_generated_token_last :val_generated_token_last'
        })
    ddb_stubber.add_response('put_item', {}, {
        'Item': {
            'user': 'u-sub',
            'tag': 'PROGRESS::PUBERTY::CORPORALITY::1::1577836800000',
            'timestamp': 1577836800000,
            'log': 'A log!',
            'data': {'key': 1234}
        },
        'ReturnValues': 'NONE',
        'TableName': 'logs'
    })

    authorizer_map = {
        "claims": {"sub": "u-sub"}
    }
    response = create_log(HTTPEvent({
        "pathParameters": {
            "sub": "u-sub",
            "tag": "PROGRESS",
        },
        "requestContext": {
            "authorizer": authorizer_map
        },
        "body": json.dumps({
            "log": "A log!",
            "data": {'key': 1234},
            "token": Task.generate_objective_token('puberty::corporality::1', Authorizer(authorizer_map))
        })
    }))
    assert response.status == 200
    Schema({
        'item': {
            'tag': 'PROGRESS::PUBERTY::CORPORALITY::1::' + str(1577836800000),
            'timestamp': 1577836800000,
            'log': 'A log!',
            'data': {'key': 1234},
            'user': 'u-sub'
        },
        'token': str
    }).validate(response.body)

    ddb_stubber.assert_no_pending_responses()
