import os
from abc import ABC
from typing import Dict, List

import boto3

from core import JSONResponse
from core.aws.errors import HTTPError
from core.utils import join_key


class Token:
    def __init__(self, access: str, expires: int, refresh: str, type_: str, id_: str):
        self.access = access
        self.expires = expires
        self.refresh = refresh
        self.id = id_
        self.type = type_

    def as_dict(self):
        return {
            "access": self.access,
            "expires": self.expires,
            "refresh": self.refresh,
            "id": self.id,
            "type": self.type
        }


class User:
    def __init__(self, username: str, attributes: Dict[str, str]):
        self.username = username
        self.attributes = attributes

    def to_dict(self):
        return {
            'username': self.username,
            'attributes': self.attributes
        }


class CognitoService(ABC):
    __user_pool_id__: str
    _client: boto3.client = None

    @classmethod
    def get_client_id(cls):
        return os.environ.get("COGNITO_CLIENT_ID", "TEST")

    @classmethod
    def get_client(cls):
        if cls._client is None:
            cls._client = boto3.client('cognito-idp', region_name='us-west-2')
        return cls._client

    @classmethod
    def get_user(cls, access_token: str):
        client = cls.get_client()
        user_dict = client.get_user(AccessToken=access_token)
        username = user_dict["Username"]
        attributes = dict()
        for attr in user_dict["UserAttributes"]:
            attributes[attr["Name"]] = attr["Value"]
        return User(username, attributes)

    @classmethod
    def sign_up(cls, username: str, password: str, attributes: dict = None):
        if attributes is None:
            attributes = {}

        client = cls.get_client()
        attributes_list = list()
        for attr_name, attr_value in attributes.items():
            attributes_list.append({
                "Name": attr_name,
                "Value": attr_value
            })

        client.sign_up(
            ClientId=cls.get_client_id(),
            Username=username,
            Password=password,
            UserAttributes=attributes_list
        )

    @classmethod
    def add_to_group(cls, username: str, group: str):
        client = cls.get_client()
        client.admin_add_user_to_group(
            UserPoolId=cls.__user_pool_id__,
            Username=username,
            GroupName=group
        )

    @classmethod
    def add_to_scout_group(cls, username: str, district: str, group: str, current_groups: List[str]):
        client = cls.get_client()
        new_group = join_key(district, group)
        if new_group in current_groups:
            return
        client.admin_update_user_attributes(
            UserPoolId=cls.__user_pool_id__,
            Username=username,
            UserAttributes=[
                {
                    'Name': 'custom:groups',
                    'Value': ','.join(current_groups + [join_key(district, group)])
                },
            ],
        )

    @classmethod
    def confirm(cls, username: str, code: str):
        client = cls.get_client()

        try:
            client.confirm_sign_up(
                ClientId=cls.get_client_id(),
                Username=username,
                ConfirmationCode=code
            )
            return JSONResponse({"message": "Confirmed account"})
        except client.exceptions.CodeMismatchException:
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, "Wrong confirmation code")
        except client.exceptions.NotAuthorizedException:
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, "Already confirmed")

    @classmethod
    def refresh(cls, token: str):
        client = cls.get_client()

        try:
            result = client.admin_initiate_auth(
                UserPoolId=cls.__user_pool_id__,
                ClientId=cls.get_client_id(),
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={
                    "REFRESH_TOKEN": token
                }
            ).get('AuthenticationResult')
            return Token(access=result.get("AccessToken"),
                         expires=result.get("ExpiresIn"),
                         type_=result.get("TokenType"),
                         refresh=None,
                         id_=result.get("IdToken"))
        except client.exceptions.InvalidPasswordException:
            return None
        except client.exceptions.NotAuthorizedException:
            return None
        except client.exceptions.UserNotFoundException:
            return None

    @classmethod
    def log_in(cls, username: str, password: str):
        client = cls.get_client()
        try:
            result = client.admin_initiate_auth(
                UserPoolId=cls.__user_pool_id__,
                ClientId=cls.get_client_id(),
                AuthFlow="ADMIN_USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": username,
                    "PASSWORD": password
                }
            ).get('AuthenticationResult')
            return Token(access=result["AccessToken"],
                         expires=result["ExpiresIn"],
                         type_=result["TokenType"],
                         refresh=result["RefreshToken"],
                         id_=result["IdToken"])
        except client.exceptions.InvalidPasswordException:
            return None
        except client.exceptions.NotAuthorizedException:
            return None
        except client.exceptions.UserNotFoundException:
            return None
