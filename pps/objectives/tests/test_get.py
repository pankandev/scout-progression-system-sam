import pytest
from botocore.stub import Stubber

from ...core import core

import sys

sys.modules['core'] = core
from ..app import Objectives, get_objective, get_objectives, process_objective


@pytest.fixture(scope="function")
def ddb_stubber():
    ddb_stubber = Stubber(Objectives.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_get_objective(ddb_stubber):
    get_item_params = {
        'TableName': 'objectives',
        'Key': {
            "unit-stage": "scouts::prepuberty",
            "code": "corporality::1"
        }
    }
    get_item_response = {'Item': {
        'unit-stage': {'S': 'scouts::prepuberty'},
        'code': {'S': 'corporality::1'},
        'description': {'S': 'Corporality objective'}
    }}
    ddb_stubber.add_response('get_item', get_item_response, get_item_params)

    result = get_objective("scouts", "prepuberty", "corporality", 1)
    assert result.item["code"] == "corporality::1"
    ddb_stubber.assert_no_pending_responses()


def test_get_objectives(ddb_stubber):
    query_params = {
        'TableName': 'objectives',
        'KeyConditions': {
            "unit-stage": {
                'AttributeValueList': ['scouts::prepuberty'],
                'ComparisonOperator': 'EQ'}
        }
    }
    query_response = {'Items': [{
        'unit-stage': {'S': 'scouts::prepuberty'},
        'code': {'S': 'corporality::1'},
        'description': {'S': 'Corporality objective'}
    }]}
    ddb_stubber.add_response('query', query_response, query_params)

    result = get_objectives("scouts", "prepuberty")
    assert result.items[0]["code"] == "corporality::1"
    ddb_stubber.assert_no_pending_responses()


def test_objective_processing():
    objective = {
        'unit-stage': 'scouts::prepuberty',
        'code': 'corporality::1',
        'description': 'Corporality objective'
    }

    process_objective(objective)
    assert objective.get("unit-stage") is None

    assert objective.get("code") == 'corporality::1'
    assert objective["unit"] == 'scouts'
    assert objective["stage"] == 'prepuberty'
    assert objective["area"] == 'corporality'
    assert objective["line"] == 1
    assert objective["description"] == 'Corporality objective'
