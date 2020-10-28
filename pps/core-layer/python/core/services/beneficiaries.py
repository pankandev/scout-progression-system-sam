from datetime import datetime, date

import botocore

from core import ModelService
from core.aws.event import Authorizer
from core.utils.consts import VALID_STAGES, VALID_AREAS
from core.utils.key import clean_text, date_to_text, join_key


class BeneficiariesService(ModelService):
    __table_name__ = "beneficiaries"
    __partition_key__ = "unit"
    __sort_key__ = "user-sub"

    @staticmethod
    def generate_code(date: datetime, nick: str):
        nick = clean_text(nick, remove_spaces=True, lower=True)
        s_date = date_to_text(date).replace('-', '')
        return join_key(nick, s_date).replace('::', '')

    @classmethod
    def get(cls, district: str, group: str, unit: str, sub: str):
        interface = cls.get_interface()
        return interface.get(join_key(district, group, unit), sub)

    @classmethod
    def calculate_stage(cls, birth_date: datetime):
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 13:
            return VALID_STAGES[0]
        else:
            return VALID_STAGES[1]

    @classmethod
    def query(cls, district: str, group: str, unit: str):
        interface = cls.get_interface()
        return interface.query(join_key(district, group, unit))

    @classmethod
    def set_target(cls, district: str, group: str, unit: str, sub: str, objective_stage: str, objective_code: str):
        interface = cls.get_interface()
        interface.update(join_key(district, group, unit), {
            "target": {
                "objective"
            }
        }, sub)

    @classmethod
    def create(cls, district: str, group: str, unit: str, authorizer: Authorizer):
        interface = cls.get_interface()

        beneficiary = {
            "full-name": authorizer.full_name,
            "nickname": authorizer.nickname,
            "birthdate": authorizer.birth_date.strftime("%d-%m-%Y"),
            "target": None,
            "objectives": None,
            "world": None,
            "score": {}
        }
        for area in VALID_AREAS:
            beneficiary["score"][area] = 0

        try:
            interface.create(join_key(district, group, unit), beneficiary, authorizer.sub, raise_if_exists_sort=True)
            return True
        except botocore.exceptions.ClientError as e:
            print(e)
            print(str(e))
            return False

