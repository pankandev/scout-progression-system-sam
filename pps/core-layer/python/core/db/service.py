from abc import ABC
from typing import Dict, Tuple, List, Any, Union

from .db import db
from .model import Operator, UpdateReturnValues
from .results import GetResult


class ModelIndex:
    def __init__(self, table_name: str, partition_key: str, sort_key: str = None, index_name: str = None):
        class TableModel(db.Model):
            __table_name__ = table_name

        self._model = TableModel
        self.partition = partition_key
        self.sort = sort_key
        self.index_name = index_name

    @property
    def client(self):
        return self._model.get_table().meta.client

    def generate_key(self, partition=None, sort=None, full=True):
        keys = dict()
        if self.sort is None and sort is not None:
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

    def create(self, partition_key, item: dict, sort_key=None, raise_if_exists_partition=False,
               raise_if_exists_sort=False, conditions: List[str] = None,
               raise_attribute_equals: dict = None):
        key = self.generate_key(partition_key, sort_key)
        must_exist = None
        if raise_if_exists_partition or raise_if_exists_sort:
            must_exist = list()
            if raise_if_exists_partition:
                must_exist.append(self.partition)
            if raise_if_exists_sort:
                must_exist.append(self.sort)
        add_result = self._model.add({**item, **key}, raise_if_attributes_exist=must_exist, conditions=conditions,
                                     raise_attribute_equals=raise_attribute_equals)
        return GetResult({'Item': add_result})

    def query(self, partition_key, sort_key: Union[List[Tuple[Operator, Any]], Tuple[Operator, Any], Any] = None,
              limit=None, start_key=None, attributes=None, scan_forward: bool = None):
        if sort_key is None:
            sort_key = []
        if isinstance(sort_key, tuple):
            sort_key = [sort_key]
        elif not isinstance(sort_key, list):
            sort_key = [(Operator.EQ, sort_key)]
        if len(sort_key) > 0 and self.sort is None:
            raise ValueError("Sort key was given but model does not have a sort key")
        return self._model.query((self.partition, partition_key), [(self.sort, *s) for s in sort_key],
                                 limit=limit, start_key=start_key, attributes=attributes, index=self.index_name,
                                 scan_forward=scan_forward)

    def get(self, partition_key, sort_key=None, attributes: List[str] = None):
        key = self.generate_key(partition_key, sort_key)
        return self._model.get(key=key, attributes=attributes)

    def delete(self, partition_key, sort_key=None):
        key = self.generate_key(partition_key, sort_key)
        self._model.delete(key)

    def update(self, partition_key, updates: dict = None, sort_key=None, append_to: dict = None,
               condition_equals: Dict[str, Any] = None, add_to: Dict[str, int] = None, conditions=None,
               return_values: UpdateReturnValues = UpdateReturnValues.UPDATED_NEW):
        key = self.generate_key(partition_key, sort_key)
        return self._model.update(key, updates=updates, append_to=append_to, condition_equals=condition_equals,
                                  add_to=add_to, return_values=return_values, conditions=conditions)


class ModelService(ABC):
    __table_name__: str
    __partition_key__: str
    __sort_key__: str = None
    __indices__: Dict[str, Tuple[str, str]] = None

    @classmethod
    def exceptions(cls):
        return cls.get_interface().client.exceptions

    @classmethod
    def get_interface(cls, index_name=None):
        index = cls.__indices__.get(index_name) if cls.__indices__ is not None else None
        if index is None:
            partition, sort = cls.__partition_key__, cls.__sort_key__
        else:
            partition, sort = index

        return ModelIndex(cls.__table_name__, partition_key=partition, sort_key=sort,
                          index_name=index_name)
