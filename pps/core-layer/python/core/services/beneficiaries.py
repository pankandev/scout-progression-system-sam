from datetime import datetime, date

import botocore

from core import ModelService
from core.aws.event import Authorizer
from core.exceptions.forbidden import ForbiddenException
from core.utils.consts import VALID_STAGES, VALID_AREAS, BASE_TARGET_COMPLETE_SCORE
from core.utils.key import clean_text, date_to_text, join_key


class BeneficiariesService(ModelService):
    __table_name__ = "beneficiaries"
    __partition_key__ = "user-sub"
    __sort_key__ = "unit"

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
    def create(cls, district: str, group: str, authorizer: Authorizer):
        interface = cls.get_interface()

        beneficiary = {
            "full-name": authorizer.full_name,
            "nickname": authorizer.nickname,
            "birthdate": authorizer.birth_date.strftime("%d-%m-%Y"),
            "target": None,
            "completed": None,
            "score": {area: 0 for area in VALID_AREAS},
            "bought_items": {}
        }

        try:
            interface.create(authorizer.sub, beneficiary, join_key(district, group, authorizer.unit),
                             raise_if_exists_sort=True)
            return True
        except botocore.exceptions.ClientError as e:
            print(str(e))
            return False

    @classmethod
    def set_target_objective(cls, district: str, group: str, authorizer: Authorizer, area: str, line: int,
                             subline: int, task: str):
        interface = cls.get_interface()

        beneficiary = {
            "target": {
                "area": area,
                "line": line,
                "subline": subline,
                "task": task
            }
        }

        try:
            interface.update(join_key(district, group, authorizer.unit), beneficiary, authorizer.sub,
                             raise_if_exists_sort=True)
            return True
        except botocore.exceptions.ClientError as e:
            print(str(e))
            return False

    @classmethod
    def complete_target(cls, district: str, group: str, authorizer: Authorizer):
        interface = cls.get_interface()
        beneficiary = interface.get(join_key(district, group, authorizer.unit), authorizer.sub, ['target'])
        if beneficiary['target'] is None:
            raise ForbiddenException("No target has been selected")
        area = beneficiary['target']['area']
        interface.update(join_key(district, group, authorizer.unit),
                         {"target": None},
                         authorizer.sub,
                         append_to={f'completed-objectives': beneficiary['target_objective']},
                         add_to={f"score.{area}": BASE_TARGET_COMPLETE_SCORE})
        return True

    @classmethod
    def buy_item(cls, district: str, group: str, area: str, authorizer: Authorizer, item_code: str, amount: int = 1):
        interface = cls.get_interface()
        interface.update(join_key(district, group, authorizer.unit),
                         None,
                         authorizer.sub,
                         add_to={
                             f'bought_items.{item_code}': amount,
                             f'score.{area}': -amount
                         })
