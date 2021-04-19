import boto3

__all__ = ['db']

from .model import create_model, AbstractModel
from core.router.environment import ENVIRONMENT


class Database:
    def __init__(self):
        self._db = boto3.resource('dynamodb', region_name=None if ENVIRONMENT.is_local else ENVIRONMENT.aws_region,
                                  endpoint_url='http://dynamodb-local:8000' if ENVIRONMENT.is_local else None)
        self.Model: AbstractModel = create_model(self._db)


db = Database()
