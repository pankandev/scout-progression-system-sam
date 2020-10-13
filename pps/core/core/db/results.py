import abc

from .capacity import ConsumedCapacity
from ..exceptions.notfound import NotFoundException


class Result(abc.ABC):
    @abc.abstractmethod
    def as_dict(self):
        pass


class QueryResult(Result):

    def __init__(self, result: dict):
        self.items = result.get('Items')
        self.count = result.get('Count'),
        self.scanned_count = result.get('ScannedCount')
        self.last_evaluated_key = result.get('LastEvaluatedKey')
        self.consumed_capacity = ConsumedCapacity.from_dict(result.get('ConsumedCapacity'))

    def as_dict(self):
        return {
            "items": self.items,
            "count": self.count,
            "last_key": self.last_evaluated_key
        }


class GetResult(Result):
    def __init__(self, result: dict):
        self.item = result.get("Item")
        self.metadata = result.get("ResponseMetadata")

    def as_dict(self):
        return self.item
