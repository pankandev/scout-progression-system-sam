import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber

from core.services.beneficiaries import BeneficiariesService
from core.services.groups import GroupsService
from core.utils import join_key


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(BeneficiariesService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_query_group(ddb_stubber: Stubber):
    params = {
        'ExpressionAttributeNames': {'#attr_group': 'group'},
        # 'ExpressionAttributeValues': {':val_group': {'S': 'district::group'}},
        'IndexName': 'ByGroup',
        'KeyConditionExpression': Key('#attr_group').eq('district::group'),
        'TableName': 'beneficiaries'}
    response = {}
    ddb_stubber.add_response('query', response, params)
    BeneficiariesService.query_group('district', 'group')
    ddb_stubber.assert_no_pending_responses()


def test_query_unit(ddb_stubber: Stubber):
    params = {
        'ExpressionAttributeNames': {
            '#attr_unit_user': 'unit-user',
            '#attr_group': 'group'
        },
        'IndexName': 'ByGroup',
        'KeyConditionExpression': Key('#attr_group').eq('district::group') & Key('#attr_unit_user').begins_with(
            'scouts::'),
        'TableName': 'beneficiaries'}
    response = {}
    ddb_stubber.add_response('query', response, params)
    BeneficiariesService.query_unit('district', 'group', 'scouts')
    ddb_stubber.assert_no_pending_responses()
