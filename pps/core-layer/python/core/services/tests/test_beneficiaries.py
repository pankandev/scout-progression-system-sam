import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber

from core.services.beneficiaries import BeneficiariesService


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(BeneficiariesService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_query_group(ddb_stubber: Stubber):
    params = {
        'IndexName': 'ByGroup',
        'KeyConditionExpression': Key('group').eq('district::group'),
        'TableName': 'beneficiaries'}
    response = {
        'Items': [
            {
                'user': {'S': 'abcABC123'},
                'unit': {'S': 'district::group::unit'},
                'unit-user': {'S': 'district::group::unit::abcABC123'},
                'full-name': {'S': 'Name'},
                'nickname': {'S': 'Name'},
                'birthdate': {'S': '01-01-2001'},
                'score': {'M': {}},
                'n_tasks': {'M': {}},
                'bought_items': {'M': {}},
                'set_base_tasks': {'BOOL': False},
            },
            {
                'user': {'S': 'abcABC1234'},
                'unit': {'S': 'district::group::unit'},
                'unit-user': {'S': 'district::group::unit::abcABC1234'},
                'full-name': {'S': 'Name'},
                'nickname': {'S': 'Name'},
                'birthdate': {'S': '01-01-2001'},
                'score': {'M': {}},
                'n_tasks': {'M': {}},
                'bought_items': {'M': {}},
                'set_base_tasks': {'BOOL': False},
            }
        ]
    }
    ddb_stubber.add_response('query', response, params)
    BeneficiariesService.query_group('district', 'group')
    ddb_stubber.assert_no_pending_responses()


def test_query_unit(ddb_stubber: Stubber):
    params = {
        'IndexName': 'ByGroup',
        'KeyConditionExpression': Key('group').eq('district::group') & Key('unit-user').begins_with('scouts::'),
        'TableName': 'beneficiaries'}
    response = {
        'Items': [
            {
                'user': {'S': 'abcABC123'},
                'unit': {'S': 'district::group::unit'},
                'unit-user': {'S': 'district::group::unit::abcABC1235'},
                'full-name': {'S': 'Name'},
                'nickname': {'S': 'Name'},
                'birthdate': {'S': '01-01-2001'},
                'score': {'M': {}},
                'n_tasks': {'M': {}},
                'bought_items': {'M': {}},
                'set_base_tasks': {'BOOL': False},
            },
            {
                'user': {'S': 'abcABC1234'},
                'unit': {'S': 'district::group::unit'},
                'unit-user': {'S': 'district::group::unit::abcABC12345'},
                'full-name': {'S': 'Name'},
                'nickname': {'S': 'Name'},
                'birthdate': {'S': '01-01-2001'},
                'score': {'M': {}},
                'n_tasks': {'M': {}},
                'bought_items': {'M': {}},
                'set_base_tasks': {'BOOL': False},
            }
        ]
    }
    ddb_stubber.add_response('query', response, params)
    BeneficiariesService.query_unit('district', 'group', 'scouts')
    ddb_stubber.assert_no_pending_responses()
