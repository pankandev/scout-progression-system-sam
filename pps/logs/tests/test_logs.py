import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber
from freezegun import freeze_time
from schema import Schema

from core.services.logs import LogsService
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
                'tag': {'S': 'u-sub::A-TAG'},
                'timestamp': {'N': str(123456)},
                'log': {'S': 'A log!'}
            },
            {
                'tag': {'S': 'u-sub::A-TAG'},
                'timestamp': {'N': str(123457)},
                'log': {'S': 'A log!'}
            }
        ]
    }, {
                                 'TableName': 'logs',
                                 'KeyConditionExpression': Key('tag').eq('u-sub::A-TAG')
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
                'tag': 'u-sub::A-TAG',
                'timestamp': 123456,
                'log': 'A log!'
            },
            {
                'tag': 'u-sub::A-TAG',
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
    ddb_stubber.add_response('put_item', {}, {
        'Item': {
            'tag': 'u-sub::PROGRESS::1234',
            'timestamp': 1577836800000,
            'log': 'A log!',
            'data': {'key': 1234}
        },
        'ReturnValues': 'NONE',
        'TableName': 'logs'
    })
    response = create_log(HTTPEvent({
        "pathParameters": {
            "sub": "u-sub",
            "tag": "PROGRESS::1234",
        },
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "u-sub"
                }
            }
        },
        "body": json.dumps({
            "log": "A log!",
            "data": {'key': 1234}
        })
    }))
    assert response.status == 200
    Schema({
        'item': {
            'tag': 'u-sub::PROGRESS::1234',
            'timestamp': 1577836800000,
            'log': 'A log!',
            'data': {'key': 1234}
        }
    }).validate(response.body)

    ddb_stubber.assert_no_pending_responses()
