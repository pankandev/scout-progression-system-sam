import json
from datetime import datetime
from unittest.mock import patch

import pytest

from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber, ANY
from core.aws.event import HTTPEvent
from core.utils.key import epoch
from dateutil.relativedelta import relativedelta
from ..app import GroupsService, create_group, BeneficiariesService, join_group, get_group_stats


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(GroupsService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_add(ddb_stubber):
    timestamp = epoch()
    with patch('core.utils.key.epoch', lambda: timestamp):
        add_item_params = {
            'TableName': 'groups',
            'Item': {
                "district": "district",
                "code": "group",
                "name": "Group",
                "beneficiary_code": ANY,
                "scouters_code": ANY,
                "scouters": {"abc123": {"name": "Name Family", "role": "creator"}},
                "creator": "abc123"
            },
            'ConditionExpression': 'attribute_not_exists(district) AND attribute_not_exists(code)',
            'ReturnValues': 'NONE'
        }
        add_item_response = {}
        ddb_stubber.add_response('put_item', add_item_response, add_item_params)
        ben_code = GroupsService.generate_beneficiary_code("district", "group")
        GroupsService.generate_beneficiary_code = lambda x, y: ben_code
        response = create_group(HTTPEvent({
            "pathParameters": {
                "district": "district"
            },
            "body": json.dumps({
                "name": "Group",
                "code": "group"
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
        }))
    assert response.body["message"] == "OK"
    ddb_stubber.assert_no_pending_responses()


def test_generate_beneficiary_code():
    code = GroupsService.generate_beneficiary_code("district", "code")
    assert len(code) == 8


def test_join(ddb_stubber: Stubber):
    beneficiary_code = GroupsService.generate_beneficiary_code("district", "group")

    group_params = {
        'TableName': 'groups',
        'Key': {
            "district": "district",
            "code": "group"
        },
        'ProjectionExpression': 'beneficiary_code'
    }
    group_response = {
        "Item": {
            "beneficiary_code": {
                "S": beneficiary_code
            }
        }
    }

    code = BeneficiariesService.generate_code(datetime.now(), "Nick Name")
    BeneficiariesService.generate_code = lambda x, y: code

    birthdate = (datetime.now() - relativedelta(years=12, day=1)).strftime("%d-%m-%Y")
    beneficiary_params = {
        'TableName': 'beneficiaries',
        'Item': {
            "birthdate": birthdate,
            "user": "u-sub",
            "group": "district::group",
            "unit-user": "scouts::u-sub",
            "full-name": "Name Family",
            "nickname": "Nick Name",
            "target": None,
            "bought_items": {},
            "completed": None,
            'set_base_tasks': False,
            'profile_picture': None,
            "generated_token_last": -1,
            "n_claimed_tokens": -1,
            "n_tasks": {
                "corporality": 0,
                "creativity": 0,
                "character": 0,
                "affectivity": 0,
                "sociability": 0,
                "spirituality": 0
            },
            "score": {
                "corporality": 0,
                "creativity": 0,
                "character": 0,
                "affectivity": 0,
                "sociability": 0,
                "spirituality": 0
            },
        },
        'ReturnValues': 'NONE',
        'ExpressionAttributeNames': {'#model_user': 'user'},
        'ConditionExpression': 'attribute_not_exists(#model_user)'
    }
    beneficiary_response = {}

    ddb_stubber.add_response('get_item', group_response, group_params)
    ddb_stubber.add_response('put_item', beneficiary_response, beneficiary_params)

    response = join_group(HTTPEvent({
        "pathParameters": {
            "district": "district",
            "group": "group"
        },
        "body": json.dumps({
            "code": beneficiary_code
        }),
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "u-sub",
                    "nickname": "Nick Name",
                    "name": "Name",
                    "family_name": "Family",
                    "cognito:username": "mail@mail.com",
                    "birthdate": birthdate,
                    "gender": "scouts",
                    "cognito:groups": ["Beneficiaries"]
                }
            }
        }
    }))
    assert response.status == 200

    ddb_stubber.assert_no_pending_responses()


def test_stats(ddb_stubber: Stubber):
    group_params = {
        'TableName': 'groups',
        'Key': {
            "district": "district",
            "code": "group"
        },
        'ProjectionExpression': 'scouters'
    }
    group_response = {
        "Item": {
            "scouters": {
                "M": {
                    "scouter-sub": {'S': "1a2b3c"}
                }
            }
        }
    }

    beneficiary_params = {
        'IndexName': 'ByGroup',
        'KeyConditionExpression': Key('group').eq('district::group'),
        'ExpressionAttributeNames': {'#attr_user': 'user', '#attr_unit_user': 'unit-user'},
        'ProjectionExpression': '#attr_user, #attr_unit_user',
        'TableName': 'beneficiaries'
    }
    beneficiary_response = {
        "Items": [
            {"user": {"S": "user-sub-1"}},
            {"user": {"S": "user-sub-2"}}
        ]
    }

    ddb_stubber.add_response('get_item', group_response, group_params)
    ddb_stubber.add_response('query', beneficiary_response, beneficiary_params)

    for u in ['user-sub-1', 'user-sub-2']:
        log_params = {
            'KeyConditionExpression': Key('user').eq(u) & Key('tag').begins_with('STATS::'),
            'ScanIndexForward': False,
            'TableName': 'logs'
        }
        ddb_stubber.add_response('query', {
            'Items': [
                {'tag': {'S': 'STATS::COMPLETED::puberty::corporality::1.1'}},
                {'tag': {'S': 'STATS::COMPLETED::puberty::corporality::1.2'}},
                {'tag': {'S': 'STATS::PROGRESS::puberty::corporality::1.3'}},
                {'tag': {'S': 'STATS::COMPLETED::puberty::corporality::1.3'}},
                {'tag': {'S': 'STATS::PROGRESS::puberty::corporality::1.3'}},
            ]
        }, log_params)

    response = get_group_stats(HTTPEvent({
        "pathParameters": {
            "district": "district",
            "group": "group"
        },
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": "u-sub",
                    "nickname": "Nick Name",
                    "name": "Name",
                    "family_name": "Family",
                    "cognito:username": "mail@mail.com",
                    "birthdate": "01-01-2020",
                    "gender": "scouts",
                    "cognito:groups": ["Beneficiaries"]
                }
            }
        }
    }))
    assert response.status == 200

    log_count = response.body['log_count']
    completed_objectives = response.body['completed_objectives']
    progress_logs = response.body['progress_logs']

    assert log_count['REWARD'] == 0
    assert log_count['COMPLETED'] == len(
        completed_objectives['user-sub-1'] + completed_objectives['user-sub-2']
    )
    assert log_count['COMPLETED'] == 3 * 2
    assert log_count['PROGRESS'] == len(
        progress_logs['user-sub-1'] + progress_logs['user-sub-2']
    )
    assert log_count['PROGRESS'] == 2 * 2

    ddb_stubber.assert_no_pending_responses()
