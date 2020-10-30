import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber

from core.services.groups import GroupsService


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(GroupsService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_query_district(ddb_stubber: Stubber):
    params = {
        'ExpressionAttributeNames': {
            '#attr_name': 'name',
            '#attr_district': 'district',
            '#attr_code': 'code',
        },
        # 'ExpressionAttributeValues': {':val_district': {'S': 'district'}},
        'KeyConditionExpression': Key('#attr_district').eq('district'),
        'ProjectionExpression': '#attr_district, #attr_name, #attr_code',
        'TableName': 'groups'
    }
    response = {}
    ddb_stubber.add_response('query', response, params)
    GroupsService.query("district")
    ddb_stubber.assert_no_pending_responses()


def test_get(ddb_stubber: Stubber):
    params = {
        'ExpressionAttributeNames': {'#model_name': 'name'},
        'Key': {'district': 'district', 'code': 'code'},
        'ProjectionExpression': 'district, code, #model_name',
        'TableName': 'groups'
    }
    response = {}
    ddb_stubber.add_response('get_item', response, params)
    GroupsService.get('district', 'code')
    ddb_stubber.assert_no_pending_responses()
