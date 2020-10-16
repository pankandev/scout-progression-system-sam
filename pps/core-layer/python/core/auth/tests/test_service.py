import pytest
from botocore.stub import Stubber, ANY

from .. import CognitoService


@pytest.fixture
def service():
    class Service(CognitoService):
        __user_pool_id__ = "users"
    return Service


@pytest.fixture
def ddb_stubber(service: CognitoService):
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(service.get_client())
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_sign_up(service: CognitoService, ddb_stubber):
    sign_up_params = {
        'ClientId': 'TEST',
        'Username': 'username',
        'Password': 'password',
        'UserAttributes': [{
            "Name": "custom:key_a",
            "Value": "value_a"
        }, {
            "Name": "custom:key_b",
            "Value": "value_b"
        }]
    }
    sign_up_response = {
        "UserConfirmed": True,
        "UserSub": "uuid"
    }
    ddb_stubber.add_response('sign_up', sign_up_response, sign_up_params)

    service.sign_up("username", "password", {
        "key_a": "value_a",
        "key_b": "value_b"
    })
    ddb_stubber.assert_no_pending_responses()
