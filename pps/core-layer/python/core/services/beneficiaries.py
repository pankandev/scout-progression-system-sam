from datetime import datetime, date
from typing import List

import botocore

from core import ModelService
from core.aws.event import Authorizer
from core.db.model import Operator, UpdateReturnValues
from core.utils.consts import VALID_STAGES, VALID_AREAS
from core.utils.key import clean_text, date_to_text, join_key


class BeneficiariesService(ModelService):
    __table_name__ = "beneficiaries"
    __partition_key__ = "user"
    __indices__ = {"ByGroup": ("group", "unit-user")}

    @staticmethod
    def generate_code(date: datetime, nick: str):
        nick = clean_text(nick, remove_spaces=True, lower=True)
        s_date = date_to_text(date).replace('-', '')
        return join_key(nick, s_date).replace('::', '')

    @classmethod
    def get(cls, sub: str, attributes: List[str] = None):
        interface = cls.get_interface()
        return interface.get(sub, attributes=attributes)

    @classmethod
    def calculate_stage(cls, birth_date: datetime):
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 13:
            return VALID_STAGES[0]
        else:
            return VALID_STAGES[1]

    @classmethod
    def query_unit(cls, district: str, group: str, unit: str):
        interface = cls.get_interface("ByGroup")
        return interface.query(join_key(district, group), (Operator.BEGINS_WITH, join_key(unit, '')))

    @classmethod
    def query_group(cls, district: str, group: str):
        interface = cls.get_interface("ByGroup")
        return interface.query(join_key(district, group))

    @classmethod
    def create(cls, district: str, group: str, authorizer: Authorizer):
        interface = cls.get_interface()

        beneficiary = {
            "group": join_key(district, group),
            "unit-user": join_key(authorizer.unit, authorizer.sub),
            "full-name": authorizer.full_name,
            "nickname": authorizer.nickname,
            "birthdate": authorizer.birth_date.strftime("%d-%m-%Y"),
            "target": None,
            "completed": None,
            "score": {area: 0 for area in VALID_AREAS},
            "bought_items": {}
        }

        try:
            interface.create(authorizer.sub, beneficiary,
                             raise_if_exists_partition=True)
            return True
        except botocore.exceptions.ClientError as e:
            print(str(e))
            return False

    @classmethod
    def buy_item(cls, authorizer: Authorizer, area: str, item_code: str, amount: int = 1):
        interface = cls.get_interface()
        interface.update(authorizer.sub, None, None, add_to={
            f'bought_items.{item_code}': amount,
            f'score.{area}': -amount
        })

    @classmethod
    def update(cls, authorizer: Authorizer, group: str = None, name: str = None, nickname: str = None,
               active_task=None, return_values: UpdateReturnValues = UpdateReturnValues.UPDATED_NEW):
        interface = cls.get_interface()
        updates = {key: value for key, value in [
            ('group', group), ('full-name', name), ('nickname', nickname), ('target', active_task)
        ] if value is not None}

        condition_equals = {}
        if active_task is not None:
            condition_equals['target'] = None
        if len(condition_equals) == 0:
            condition_equals = None

        return interface.update(authorizer.sub, updates, None, return_values=return_values,
                                condition_equals=condition_equals)

    @classmethod
    def clear_active_task(cls, authorizer: Authorizer,
                          return_values: UpdateReturnValues = UpdateReturnValues.UPDATED_OLD):
        interface = cls.get_interface()
        updates = {'target': None}
        return interface.update(authorizer.sub, updates, None, return_values=return_values)["Attributes"]

    @classmethod
    def update_active_task(cls, authorizer: Authorizer, description: str, tasks: list):
        interface = cls.get_interface()
        updates = {
            'target.personal-objective': description,
            'target.tasks': tasks
        }
        return interface.update(authorizer.sub, updates, None, return_values=UpdateReturnValues.UPDATED_NEW) \
            .get('Attributes')
