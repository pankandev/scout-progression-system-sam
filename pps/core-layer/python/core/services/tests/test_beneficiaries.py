import pytest
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
    params = {'ExpressionAttributeValues': {':val_0': {'S': 'district::group'}},
              'IndexName': 'ByGroup',
              'KeyConditionExpression': 'group = :val_0',
              'TableName': 'beneficiaries'}
    response = {}
    ddb_stubber.add_response('query', response, params)
    BeneficiariesService.query_group('district', 'group')
    ddb_stubber.assert_no_pending_responses()


def test_query_unit(ddb_stubber: Stubber):
    params = {
        'ExpressionAttributeNames': {
            '#model_unit_user': 'unit-user'
        },
        'ExpressionAttributeValues': {
            ':val_0': {'S': 'district::group'},
            ':val_1': {'S': 'scouts'}
        },
        'IndexName': 'ByGroup',
        'KeyConditionExpression': 'group = :val_0 AND begins_with(#model_unit_user, :val_1)',
        'TableName': 'beneficiaries'}
    response = {}
    ddb_stubber.add_response('query', response, params)
    BeneficiariesService.query('district', 'group', 'scouts')
    ddb_stubber.assert_no_pending_responses()
