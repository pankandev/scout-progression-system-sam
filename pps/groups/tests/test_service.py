import json
from datetime import datetime

import pytest
from botocore.stub import Stubber, ANY

from core import HTTPEvent
from core.utils.key import generate_code, split_key
from ..app import GroupsService, create_group, validate_beneficiary_code


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
            "beneficiary_code": ANY
        },
        'ReturnValues': 'NONE'
    }
    add_item_response = {}
    ddb_stubber.add_response('put_item', add_item_response, add_item_params)
    create_group("district", {
        "name": "Group"
    })
    ddb_stubber.assert_no_pending_responses()


def test_generate_beneficiary_code():
    code = GroupsService.generate_beneficiary_code("district", "code", "Group")
    num, district, group = split_key(code)
    assert len(num) == 8
    assert district == "district"
    assert group == "group"


def test_validate_code(ddb_stubber):
    code = "01234567::district::group"

    params = {
        'TableName': 'groups',
        'Key': {
            "district": "district",
            "beneficiary-code": code
        },
        'ProjectionExpression': 'district, code, name'
    }
    response = {
        "Item": {
            "name": {
                "S": "Group"
            }
        }
    }
    ddb_stubber.add_response('get_item', response, params)

    response = validate_beneficiary_code(HTTPEvent({
        "body": json.dumps({
            "code": code
        })
    })).as_dict()
    assert json.loads(response["body"])["message"] == "Code is OK"

    ddb_stubber.assert_no_pending_responses()
