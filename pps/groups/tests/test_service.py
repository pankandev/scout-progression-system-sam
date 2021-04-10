from datetime import datetime
from unittest.mock import patch

import pytest
from botocore.stub import Stubber, ANY
from dateutil.relativedelta import relativedelta

from core.aws.event import Authorizer
from core.utils.key import epoch
from ..app import GroupsService, create_group, BeneficiariesService, join_group


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
        response = create_group("district", {
            "name": "Group",
            "code": "group"
        }, Authorizer({
            "claims": {
                "sub": "abc123",
                "name": "Name",
                "family_name": "Family"
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

    response = join_group("district", "group", beneficiary_code, Authorizer({
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
    }))
    assert response.body["message"] == "OK"

    ddb_stubber.assert_no_pending_responses()
