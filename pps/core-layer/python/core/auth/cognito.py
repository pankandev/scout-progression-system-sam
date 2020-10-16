import os
from abc import ABC

import boto3


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
