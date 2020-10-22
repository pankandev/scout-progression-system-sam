from abc import ABC
from typing import Dict, Tuple

from .db import db


class ModelIndex:
    def __init__(self, table_name: str, partition_key: str, sort_key: str = None, index_name: str = None):
        class TableModel(db.Model):
            __table_name__ = table_name

        self._model = TableModel
        self.partition = partition_key
        self.sort = sort_key
        self.index_name = index_name

    def generate_key(self, partition=None, sort=None, full=True):
        keys = dict()
        if sort is not None and self.sort is None:
            raise ValueError("Sort key was given but model does not have a sort key")

        if full:
            if self.partition is not None and partition is None:
                raise ValueError("Partition key cannot be None")
            if self.sort is not None and sort is None:
                raise ValueError("Sort key cannot be None")
        if partition is not None:
            keys[self.partition] = partition
        if sort is not None:
            keys[self.sort] = sort
        return keys

    def create(self, partition_key, item: dict, sort_key=None, raise_if_exists=False):
        key = self.generate_key(partition_key, sort_key)
        if not raise_if_exists:
            condition = None
        elif self.sort is not None:
            condition = f'attribute_not_exists({self.partition}) AND attribute_not_exists({self.sort})'
        else:
            condition = f'attribute_not_exists({self.partition})'
        self._model.add({**item, **key}, condition=condition)

    def query(self, partition_key=None, sort_key=None, limit=None, start_key=None, attributes=None):
        no_key = partition_key is None and sort_key is None
        key = None if no_key else self.generate_key(partition_key, sort_key, False)
        return self._model.query(keys=key, limit=limit, start_key=start_key, attributes=attributes,
                                 index=self.index_name)

    def get(self, partition_key, sort_key=None, attributes=None):
        key = self.generate_key(partition_key, sort_key)
        return self._model.get(key=key, attributes=attributes)

    def delete(self, partition_key, sort_key=None):
        key = self.generate_key(partition_key, sort_key)
        self._model.delete(key)

    def update(self, partition_key, updates: dict, sort_key=None):
        key = self.generate_key(partition_key, sort_key)
        self._model.update(key, updates)


class ModelService(ABC):
    __table_name__: str
    __partition_key__: str
    __sort_key__: str = None
    __indices__: Dict[str, Tuple[str, str]] = None

    @classmethod
    def get_interface(cls, index_name=None):
        index = cls.__indices__.get(index_name) if cls.__indices__ is not None else None
        if index is None:
            partition, sort = cls.__partition_key__, cls.__sort_key__
        else:
            partition, sort = index

        return ModelIndex(cls.__table_name__, partition_key=partition, sort_key=sort,
                          index_name=index_name)
