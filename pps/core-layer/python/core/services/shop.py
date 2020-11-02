import time

from core import ModelService
from core.db.model import Operator


class ShopService(ModelService):
    __table_name__ = "items"
    __partition_key__ = "category"
    __sort_key__ = "release-id"

    @classmethod
    def create(cls, name: str, description: str, price: int, category: str, release: int):
        index = cls.get_interface()

        ms_time = int(time.time() * 1000)
        release_id = int(release * 100000 + ms_time % 100000)

        item = {
            'name': name,
            'description': description,
            'price': price
        }
        return index.create(category, item, release_id, raise_if_exists_sort=True, raise_if_exists_partition=True)

    @classmethod
    def query(cls, category: str, release: int):
        index = cls.get_interface()
        result = index.query(category, (Operator.LESS_THAN, int((release + 1) * 1e5)),
                             attributes=['name', 'category', 'description', 'release-id', 'price'])
        for item in result.items:
            release = int(item['release-id'] // 100000)
            id_ = int(item['release-id'] % 100000)
            item['release'] = release
            item['id'] = id_
            del item['release-id']
        return result

    @classmethod
    def get(cls, category: str, release: int, id_: int):
        index = cls.get_interface()
        release_id = release * 100000 + id_
        result = index.get(category, release_id, attributes=['name', 'category', 'description', 'release-id', 'price'])
        if result.item is None:
            return result

        release = result.item['release-id'] // 100000
        id_ = result.item['release-id'] % 100000
        result.item['release'] = release
        result.item['id'] = id_
        return result
