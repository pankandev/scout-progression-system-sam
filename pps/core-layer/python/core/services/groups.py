import hashlib
import os
import random

from core import ModelService
from core.auth import CognitoService
from core.aws.event import Authorizer
from core.exceptions.invalid import InvalidException
from core.utils import join_key
from core.utils.key import split_key
from schema import Schema

schema = Schema({
    'name': str,
})


class UsersCognito(CognitoService):
    __user_pool_id__ = os.environ.get("USER_POOL_ID", "TEST_POOL")


class GroupsService(ModelService):
    __table_name__ = "groups"
    __partition_key__ = "district"
    __sort_key__ = "code"
    __indices__ = {}

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
    def join_as_scouter(cls, authorizer: Authorizer, district: str, group: str, code: str):
        interface = cls.get_interface()
        try:
            interface.update(district, {
                'scouters.' + authorizer.sub: {
                    'name': authorizer.full_name,
                    'role': 'scouter'
                }
            }, group, condition_equals={'scouters_code': code})
        except cls.exceptions().ConditionalCheckFailedException:
            raise InvalidException('Wrong scouters code')
        UsersCognito.add_to_scout_group(authorizer.username, district, group, authorizer.scout_groups)

    @classmethod
    def init(cls, district: str, group: str, creator_email: str, full_name: str):
        UsersCognito.add_to_scout_group(creator_email, district, group, [])

        interface = cls.get_interface()
        interface.update(district, {
            'scouters.' + creator_email: {
                'name': full_name,
                'role': 'creator'
            }
        }, group)
