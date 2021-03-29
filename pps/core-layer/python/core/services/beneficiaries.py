from datetime import datetime, date
from typing import List, Dict, Any, Union

import botocore
from boto3.dynamodb.conditions import Attr

from core import ModelService
from core.aws.event import Authorizer
from core.db.model import Operator, UpdateReturnValues
from core.exceptions.invalid import InvalidException
from core.services.rewards import RewardsService
from core.utils.consts import VALID_STAGES, VALID_AREAS
from core.utils.key import clean_text, date_to_text, join_key, split_key


class Beneficiary:
    user_sub: str
    district: str
    group: str
    unit: str
    birthdate: datetime
    full_name: str
    nickname: str
    score: Dict[str, int]
    n_tasks: Dict[str, int]
    target: Any
    bought_items: Dict[int, str]
    set_base_tasks: Union[bool, None]

    def __init__(self, user_sub: str, full_name: str, nickname: str, district: str, group: str, unit: str,
                 score: Dict[str, int], n_tasks: Dict[str, int], birthdate: datetime, target: Any,
                 bought_items: Dict[int, str], set_base_tasks: Union[bool, None]):
        self.user_sub = user_sub
        self.district = district
        self.group = group
        self.unit = unit
        self.birthdate = birthdate
        self.full_name = full_name
        self.nickname = nickname
        self.score = {area: score.get(area, 0) for area in VALID_AREAS}
        self.n_tasks = {area: n_tasks.get(area, 0) for area in VALID_AREAS}
        self.target = target
        self.bought_items = bought_items
        self.set_base_tasks = set_base_tasks

    @staticmethod
    def from_db_map(beneficiary: dict):
        from core.services.tasks import Task

        user_sub = beneficiary["user"]
        district, group, unit = beneficiary["unit"].split("::")
        unit = split_key(beneficiary["unit-user"])[0]
        full_name = beneficiary["full-name"]
        nickname = beneficiary["nickname"]
        birthdate = datetime.strptime(beneficiary["birthdate"], "%d-%m-%Y")
        score = {area: beneficiary["score"].get(area, 0) for area in VALID_AREAS}
        n_tasks = {area: beneficiary["n_tasks"].get(area, 0) for area in VALID_AREAS}
        target = Task.from_db_dict(beneficiary["target"]) if beneficiary.get("target") is not None else None
        bought_items = beneficiary["bought_items"]
        set_base_tasks = beneficiary["set_base_tasks"]

        return Beneficiary(user_sub=user_sub, full_name=full_name, nickname=nickname, district=district, group=group,
                           unit=unit, score=score, n_tasks=n_tasks, birthdate=birthdate, target=target,
                           bought_items=bought_items, set_base_tasks=set_base_tasks)

    def to_db_dict(self):
        return {
            "user": self.user_sub,
            "group": join_key(self.district, self.group),
            "unit-user": join_key(self.unit, self.user_sub),
            "full-name": self.full_name,
            "nickname": self.nickname,
            "birthdate": self.birthdate.strftime("%d-%m-%Y"),
            "target": self.target.to_dict() if self.target is not None else None,
            "completed": None,
            "score": {area: self.score.get(area, 0) for area in VALID_AREAS},
            "n_tasks": {area: self.score.get(area, 0) for area in VALID_AREAS},
            "set_base_tasks": self.set_base_tasks,
            "bought_items": {}
        }

    def to_api_dict(self):
        return {
            "district": self.district,
            "group": self.group,
            "unit": self.unit,
            "full-name": self.full_name,
            "nickname": self.nickname,
            "stage": BeneficiariesService.calculate_stage(self.birthdate),
        }


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

        beneficiary = Beneficiary(
            user_sub=authorizer.sub,
            district=district,
            group=group,
            unit=authorizer.unit,
            full_name=authorizer.full_name,
            nickname=authorizer.nickname,
            birthdate=authorizer.birth_date,
            target=None,
            set_base_tasks=None,
            score={area: 0 for area in VALID_AREAS},
            n_tasks={area: 0 for area in VALID_AREAS},
            bought_items={}
        )

        try:
            interface.create(authorizer.sub, beneficiary.to_db_dict(),
                             raise_if_exists_partition=True)
            return True
        except botocore.exceptions.ClientError as e:
            print(str(e))
            return False

    @classmethod
    def buy_item(cls, authorizer: Authorizer, area: str, item_category: str, item_release: int, item_id: int,
                 amount: int = 1):
        interface = cls.get_interface()
        item = RewardsService.get(item_category, item_release, item_id).item
        if item is None:
            return False

        price = item.get('price')
        if price is None:
            raise InvalidException('This rewards cannot be bought')

        release_id = item_release * 100000 + item_id
        return interface.update(authorizer.sub, None, None, add_to={
            f'bought_items.{item_category}{release_id}': amount,
            f'score.{area}': int(-amount * price)
        }, conditions=Attr(f'score.{area}').gte(int(amount * price)), return_values=UpdateReturnValues.UPDATED_NEW)[
            'Attributes']

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
                          return_values: UpdateReturnValues = UpdateReturnValues.UPDATED_OLD,
                          receive_score=False
                          ):
        interface = cls.get_interface()
        updates = {'target': None}
        add_to = None
        if receive_score:
            beneficiary = BeneficiariesService.get(authorizer.sub, ["target.objective"]).item

            if beneficiary.get('target') is None:
                return None
            score = 80
            area = split_key(beneficiary['target']['objective'])[1]
            add_to = {
                f'score.{area}': score,
                f'n_tasks.{area}': 1
            }

        return interface.update(authorizer.sub, updates, None, return_values=return_values,
                                add_to=add_to)["Attributes"]

    @classmethod
    def update_active_task(cls, authorizer: Authorizer, description: str, tasks: list):
        interface = cls.get_interface()
        updates = {
            'target.personal-objective': description,
            'target.tasks': tasks
        }
        return interface.update(authorizer.sub, updates, None, return_values=UpdateReturnValues.UPDATED_NEW) \
            .get('Attributes')

    @classmethod
    def mark_as_initialized(cls, authorizer: Authorizer):
        interface = cls.get_interface()
        updates = {
            'set_base_tasks': False,
        }
        try:
            return interface.update(authorizer.sub, updates, return_values=UpdateReturnValues.UPDATED_NEW,
                                    conditions=Attr('set_base_tasks').eq(None))
        except interface.client.exceptions.ConditionalCheckFailedException:
            raise InvalidException('Beneficiary already initialized')
