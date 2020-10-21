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
            "Name": "key_a",
            "Value": "value_a"
        }, {
            "Name": "key_b",
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


def test_log_in(service: CognitoService, ddb_stubber):
    log_in_params = {
        'AuthFlow': 'ADMIN_USER_PASSWORD_AUTH',
        'ClientId': 'TEST',
        'UserPoolId': 'users',
        'AuthParameters': {
            "USERNAME": "username",
            "PASSWORD": "password"
        }
    }
    log_in_response = {
        'AuthenticationResult': {
            'AccessToken': 'access',
            'ExpiresIn': 123,
            'TokenType': 'Bearer',
            'RefreshToken': 'refresh',
            'IdToken': 'id'
        }
    }
    ddb_stubber.add_response('admin_initiate_auth', log_in_response, log_in_params)
    token = service.log_in("username", "password")
    assert token.type == 'Bearer'
    assert token.id == 'id'
    assert token.refresh == 'refresh'
    assert token.expires == 123
    assert token.access == 'access'
    ddb_stubber.assert_no_pending_responses()


def test_get_user(service: CognitoService, ddb_stubber):
    params = {
        'AccessToken': 'abc123'
    }
    response = {
        'Username': 'username',
        'UserAttributes': [
            {'Name': 'keyA', 'Value': 'valueA'},
            {'Name': 'keyB', 'Value': 'valueB'}
        ]
    }

    ddb_stubber.add_response('get_user', response, params)
    user = service.get_user('abc123')
    assert user.username == 'username'
    assert len(user.attributes) == 2
    assert user.attributes['keyA'] == 'valueA'
    assert user.attributes['keyB'] == 'valueB'
    ddb_stubber.assert_no_pending_responses()
