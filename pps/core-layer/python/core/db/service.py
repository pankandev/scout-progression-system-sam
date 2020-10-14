from abc import ABC

from .db import db


class ModelInterface:
    def __init__(self, table_name: str, partition_key: str, sort_key: str = None):
        class TableModel(db.Model):
            __table_name__ = table_name
        self._model = TableModel
        self.partition = partition_key
        self.sort = sort_key

    def generate_key(self, partition=None, sort=None, full=True):
        keys = dict()
        if sort is not None and self.sort is None:
            raise ValueError("Sort key was given but model does not have a sort key")

        print(full, self.sort)
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

    def create(self, partition_key, item: dict, sort_key=None):
        key = self.generate_key(partition_key, sort_key)
        print(item, key)
        self._model.add({**item, **key})

    def query(self, partition_key=None, sort_key=None, limit=None, start_key=None, attributes=None, index=None):
        no_key = partition_key is None and sort_key is None
        key = None if no_key else self.generate_key(partition_key, sort_key, False)
        print(key)
        return self._model.query(keys=key, limit=limit, start_key=start_key, attributes=attributes, index=index)

    def get(self, partition_key, sort_key=None, attributes=None):
        key = self.generate_key(partition_key, sort_key)
        return self._model.get(key=key)

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
    _interface: ModelInterface = None

    @classmethod
    def get_interface(cls):
        if cls._interface is None:
            cls._interface = ModelInterface(cls.__table_name__, cls.__partition_key__, cls.__sort_key__)
        return cls._interface
