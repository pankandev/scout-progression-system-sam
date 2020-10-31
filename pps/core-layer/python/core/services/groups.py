import hashlib
import random
from typing import Any

from schema import Schema

from core import ModelService
from core.utils import join_key
from core.utils.key import split_key

schema = Schema({
    'name': str,
})


class GroupsService(ModelService):
    __table_name__ = "groups"
    __partition_key__ = "district"
    __sort_key__ = "code"
    __indices__ = {
        "ByBeneficiaryCode": ("code", "beneficiary-code")
    }

    @property
    def exceptions(self) -> Any:
        return self.get_interface().client.exceptions

    @staticmethod
    def generate_beneficiary_code(district: str, group_code: str):
        h = hashlib.sha1(join_key(district, group_code).encode()).hexdigest()
        int_hash = (int(h, 16) + random.randint(0, 1024)) % (10 ** 8)
        return f'{int_hash:08}'

    @staticmethod
    def generate_scouters_code(district: str, group_code: str):
        return hashlib.sha1(join_key(district, group_code).encode()).hexdigest()

    @staticmethod
    def process_beneficiary_code(code: str):
        num, district, group = split_key(code)
        return {
            "district": district,
            "code": num,
            "group": group
        }

    @classmethod
    def create(cls, code: str, district: str, item: dict, creator_sub: str, creator_full_name: str):
        interface = cls.get_interface()
        group = schema.validate(item)
        group['beneficiary_code'] = cls.generate_beneficiary_code(district, code)
        group['scouters_code'] = cls.generate_scouters_code(district, code)
        group['creator'] = creator_sub
        group['scouters'] = {
            creator_sub: {
                "name": creator_full_name,
                "role": "creator"
            }
        }
        interface.create(code, group, district, raise_if_exists_partition=True, raise_if_exists_sort=True)

    @classmethod
    def get(cls, district: str, code: str, attributes: list = None):
        if attributes is None:
            attributes = ["district", "code", "name"]

        interface = cls.get_interface()
        return interface.get(district, code, attributes=attributes)

    @classmethod
    def query(cls, district: str):
        interface = cls.get_interface()
        return interface.query(district, attributes=["district", "name", "code"])

    @classmethod
    def get_by_code(cls, code: str):
        processed = GroupsService.process_beneficiary_code(code)
        district = processed["district"]

        interface = cls.get_interface("ByBeneficiaryCode")
        return interface.get(district, code, attributes=["district", "code", "name"])
