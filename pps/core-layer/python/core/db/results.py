import abc
from decimal import Decimal

from .capacity import ConsumedCapacity


class Result(abc.ABC):
    @abc.abstractmethod
    def as_dict(self):
        pass


def clean_value(value):
    if type(value) is Decimal:
        return float(value)
    return value


def clean_item(item: dict):
    if item is None:
        return None
    return {
        key: clean_item(value) if type(value) is dict else clean_value(value) for key, value in item.items()
    }


class QueryResult(Result):

    def __init__(self, result: dict):
        print(result)
        uncleaned_items = result.get('Items')
        self.items = [clean_item(item) for item in uncleaned_items] if uncleaned_items is not None else None
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
        self.item = clean_item(result.get("Item"))
        self.metadata = result.get("ResponseMetadata")

    @classmethod
    def from_item(cls, item):
        return GetResult({'Item': item})

    def as_dict(self):
        return self.item
