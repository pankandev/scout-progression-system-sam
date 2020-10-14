import boto3

__all__ = ['db']

from .model import create_model, AbstractModel


class Database:
    def __init__(self):
        self._db = boto3.resource('dynamodb', region_name='us-west-2')
        self.Model: AbstractModel = create_model(self._db)


db = Database()
