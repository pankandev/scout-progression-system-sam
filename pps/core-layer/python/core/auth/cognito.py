import os
from abc import ABC


class CognitoService(ABC):
    __user_pool_id__: str

    @staticmethod
    def client_id():
        return os.environ.get("COGNITO_CLIENT_ID")
