import os
from abc import ABC

import boto3

from core import JSONResponse
from core.aws.errors import HTTPError


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
            "expires": self.access,
            "refresh": self.refresh,
            "id": self.id,
            "type": self.type
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
    def sign_up(cls, username: str, password: str, attributes: dict = None):
        if attributes is None:
            attributes = {}

        client = cls.get_client()
        attributes_list = list()
        for attr_name, attr_value in attributes.items():
            attributes_list.append({
                "Name": f"custom:{attr_name}",
                "Value": attr_value
            })

        client.sign_up(
            ClientId=cls.get_client_id(),
            Username=username,
            Password=password,
            UserAttributes=attributes_list
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
    def log_in(cls, username: str, password: str):
        client = cls.get_client()
        try:
            result = client.admin_initiate_auth(
                UserPoolId=cls.__user_pool_id__,
                ClientId=cls.get_client_id(),
                AuthFlow="USER_PASSWORD_AUTH",
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
        except client.exceptions.AccessDeniedException:
            return None
