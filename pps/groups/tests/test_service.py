from datetime import datetime

import pytest
from botocore.stub import Stubber, ANY

from core.aws.event import Authorizer
from core.utils.key import generate_code, join_key
from ..app import GroupsService, create_group, UsersCognito, BeneficiariesService, join_group


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(GroupsService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_add(ddb_stubber):
    add_item_params = {
        'TableName': 'groups',
        'Item': {
            "district": "district",
            "code": generate_code("Group"),
            "name": "Group",
            "beneficiary_code": ANY,
            "scouters": [],
            "creator": {
                "name": "Name Family",
                "sub": "abc123"
            }
        },
        'ReturnValues': 'NONE'
    }
    add_item_response = {}
    ddb_stubber.add_response('put_item', add_item_response, add_item_params)
    ben_code = GroupsService.generate_beneficiary_code("district", "group", "Group")
    GroupsService.generate_beneficiary_code = lambda x, y, z: ben_code
    response = create_group("district", {
        "name": "Group"
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
    code = GroupsService.generate_beneficiary_code("district", "code", "Group")
    assert len(code) == 8


def test_join(ddb_stubber: Stubber):
    beneficiary_code = GroupsService.generate_beneficiary_code("district", "group", "Group")

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

    unit_code = join_key("district", "group", "scouts")

    code = BeneficiariesService.generate_code(datetime.now(), "Nick Name")
    BeneficiariesService.generate_code = lambda x, y: code

    beneficiary_params = {
        'TableName': 'beneficiaries',
        'Item': {
            "unit": unit_code,
            "code": code,
            "sub": "user-sub",
            "full-name": "Name Family",
            "nickname": "Nick Name",
            "tasks": []
        },
        'ReturnValues': 'NONE'
    }
    beneficiary_response = {
    }

    ddb_stubber.add_response('get_item', group_response, group_params)
    ddb_stubber.add_response('put_item', beneficiary_response, beneficiary_params)

    response = join_group("district", "group", "scouts", beneficiary_code, Authorizer({
        "claims": {
            "sub": "user-sub",
            "nickname": "Nick Name",
            "name": "Name",
            "family_name": "Family",
        }
    }))
    assert response.body["message"] == "OK"

    ddb_stubber.assert_no_pending_responses()
