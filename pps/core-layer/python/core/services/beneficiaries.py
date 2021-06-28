from datetime import datetime, date
from typing import List, Dict, Union

from boto3.dynamodb.conditions import Attr
from core import ModelService
from core.aws.event import Authorizer
from core.db.model import Operator, UpdateReturnValues
from core.exceptions.invalid import InvalidException
from core.exceptions.notfound import NotFoundException
from core.services.logs import LogsService, LogKey
from core.services.rewards import RewardsService, Reward
from core.services.tasks import Task
from core.utils.consts import VALID_STAGES, VALID_AREAS
from core.utils.key import clean_text, date_to_text, join_key, split_key
from schema import Schema, Or


class Beneficiary:
    user_sub: str
    district: str
    group: str
    unit: str
    birthdate: datetime
    full_name: str
    nickname: str
    profile_picture: str
    score: Dict[str, int]
    n_tasks: Dict[str, int]
    target: Union[Task, None]
    bought_items: Dict[int, str]
    set_base_tasks: Union[bool, None]
    generated_token_last: int
    n_claimed_tokens: int

    def __init__(self, user_sub: str, full_name: str, nickname: str, district: str, group: str, unit: str,
                 score: Dict[str, int], n_tasks: Dict[str, int], birthdate: datetime, target: Union[Task, None],
                 bought_items: Dict[int, str], set_base_tasks: Union[bool, None], generated_token_last: int = -1,
                 n_claimed_tokens: int = -1, profile_picture: str = None):
        self.user_sub = user_sub
        self.district = district
        self.group = group
        self.unit = unit
        self.birthdate = birthdate
        self.full_name = full_name
        self.nickname = nickname
        self.profile_picture = profile_picture
        self.score = {area: score.get(area, 0) for area in VALID_AREAS} if score is not None else None
        self.n_tasks = {area: n_tasks.get(area, 0) for area in VALID_AREAS} if n_tasks is not None else None
        self.target = target
        self.bought_items = bought_items
        self.set_base_tasks = set_base_tasks
        self.generated_token_last = generated_token_last
        self.n_claimed_tokens = n_claimed_tokens

    @staticmethod
    def from_db_map(beneficiary: dict):
        if beneficiary is None:
            return None

        from core.services.tasks import Task

        user_sub = beneficiary.get("user")

        district_group = beneficiary.get("group")
        district, group = district_group.split("::") if district_group is not None else (None, None)

        unit_user = beneficiary.get("unit-user")
        unit = split_key(unit_user)[0] if unit_user is not None else None

        full_name = beneficiary.get("full-name")
        nickname = beneficiary.get("nickname")

        raw_birthdate = beneficiary.get("birthdate")
        birthdate = datetime.strptime(raw_birthdate, "%d-%m-%Y") if raw_birthdate is not None else None

        score = beneficiary.get("score")
        score = {area: int(score.get(area, 0)) for area in VALID_AREAS} if score is not None else None

        n_tasks = beneficiary.get("n_tasks")
        n_tasks = {area: int(n_tasks.get(area, 0)) for area in VALID_AREAS} if n_tasks is not None else None

        target = beneficiary.get("target")
        target = Task.from_db_dict(target) if target is not None else None

        bought_items = beneficiary.get("bought_items")
        set_base_tasks = beneficiary.get("set_base_tasks", False)

        generated_token_last = int(beneficiary.get("generated_token_last", -1))
        n_claimed_tokens = int(beneficiary.get("n_claimed_tokens", -1))

        profile_picture = beneficiary.get('profile_picture')

        return Beneficiary(user_sub=user_sub, full_name=full_name, nickname=nickname, district=district, group=group,
                           unit=unit, score=score, n_tasks=n_tasks, birthdate=birthdate, target=target,
                           bought_items=bought_items, set_base_tasks=set_base_tasks, n_claimed_tokens=n_claimed_tokens,
                           generated_token_last=generated_token_last, profile_picture=profile_picture)

    def to_db_dict(self):
        return {
            "user": self.user_sub,
            "group": join_key(self.district, self.group),
            "unit-user": join_key(self.unit, self.user_sub),
            "profile_picture": self.profile_picture,
            "full-name": self.full_name,
            "nickname": self.nickname,
            "birthdate": self.birthdate.strftime("%d-%m-%Y"),
            "target": self.target.to_db_dict() if self.target is not None else None,
            "completed": None,
            "score": {area: self.score.get(area, 0) for area in VALID_AREAS},
            "n_tasks": {area: self.score.get(area, 0) for area in VALID_AREAS},
            "set_base_tasks": self.set_base_tasks,
            "bought_items": {},
            "generated_token_last": self.generated_token_last,
            "n_claimed_tokens": self.n_claimed_tokens
        }

    def to_api_dict(self, full=True):
        return {
            "id": self.user_sub,
            "district": self.district,
            "group": self.group,
            "profile_picture": self.profile_picture,
            "unit": self.unit,
            "full-name": self.full_name,
            "nickname": self.nickname,
            "stage": BeneficiariesService.calculate_stage(self.birthdate),
            "birthdate": self.birthdate.strftime("%d-%m-%Y"),
            "bought_items": self.bought_items,
            "n_tasks": {area: self.score.get(area, 0) for area in VALID_AREAS},
            "target": self.target.to_api_dict() if self.target is not None else None,
            "score": {area: self.score.get(area, 0) for area in VALID_AREAS},
            "last_claimed_token": self.n_claimed_tokens,
            "set_base_tasks": self.set_base_tasks,
        } if full else {
            "id": self.user_sub,
            "district": self.district,
            "group": self.group,
            "profile_picture": self.profile_picture,
            "unit": self.unit,
            "full-name": self.full_name,
            "nickname": self.nickname,
            "stage": BeneficiariesService.calculate_stage(self.birthdate),
            "birthdate": self.birthdate.strftime("%d-%m-%Y"),
            "n_tasks": {area: self.score.get(area, 0) for area in VALID_AREAS},
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
    def get(cls, sub: str, attributes: List[str] = None) -> Beneficiary:
        interface = cls.get_interface()
        result = interface.get(sub, attributes=attributes)
        return Beneficiary.from_db_map(result.item)

    @classmethod
    def calculate_stage(cls, birth_date: datetime):
        today = date.today()
        age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
        if age < 13:
            return VALID_STAGES[0]
        else:
            return VALID_STAGES[1]

    @classmethod
    def query_unit(cls, district: str, group: str, unit: str, attributes: List[str] = None):
        interface = cls.get_interface("ByGroup")
        result = interface.query(join_key(district, group), (Operator.BEGINS_WITH, join_key(unit, '')),
                                 attributes=attributes)
        result.items = [Beneficiary.from_db_map(item) for item in result.items]
        return result

    @classmethod
    def query_group(cls, district: str, group: str, attributes: List[str] = None) -> List[Beneficiary]:
        interface = cls.get_interface("ByGroup")
        return [Beneficiary.from_db_map(item) for item in
                interface.query(join_key(district, group), attributes=attributes).items]

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
            set_base_tasks=False,
            score={area: 0 for area in VALID_AREAS},
            n_tasks={area: 0 for area in VALID_AREAS},
            bought_items={}
        )

        try:
            interface.create(authorizer.sub, beneficiary.to_db_dict(),
                             raise_if_exists_partition=True)
        except cls.exceptions().ConditionalCheckFailedException:
            raise InvalidException("Already joined a group")

    @classmethod
    def buy_item(cls, authorizer: Authorizer, area: str, item_category: str, item_release: int, item_id: int,
                 amount: int = 1):
        interface = cls.get_interface()
        item = RewardsService.get(item_category, item_release, item_id).item
        if item is None:
            return False

        price = item.get('price')
        if price is None:
            raise InvalidException('This reward cannot be bought')

        release_id = item_release * 100000 + item_id
        return interface.update(authorizer.sub, None, None, add_to={
            f'bought_items.{item_category}{release_id}': amount,
            f'score.{area}': int(-amount * price)
        }, conditions=Attr(f'score.{area}').gte(int(amount * price)), return_values=UpdateReturnValues.UPDATED_NEW)[
            'Attributes']

    @classmethod
    def update(cls, authorizer: Authorizer, group: str = None, name: str = None, nickname: str = None,
               profile_picture: str = None, active_task=None,
               return_values: UpdateReturnValues = UpdateReturnValues.UPDATED_NEW):
        interface = cls.get_interface()
        updates = {key: value for key, value in [
            ('group', group), ('full-name', name), ('nickname', nickname), ('target', active_task),
            ('profile_picture', profile_picture)
        ] if value is not None}

        condition_equals = {}
        if active_task is not None:
            condition_equals['target'] = None
        if len(condition_equals) == 0:
            condition_equals = None

        return interface.update(authorizer.sub, updates, None, return_values=return_values,
                                condition_equals=condition_equals)

    @classmethod
    def set_reward_index(cls, authorizer: Authorizer, index: int):
        interface = cls.get_interface()
        updates = {'n_claimed_tokens': index}
        conditions = "#attr_n_claimed_tokens < :val_n_claimed_tokens"
        try:
            return interface.update(authorizer.sub, updates, None, conditions=conditions)
        except interface.client.exceptions.ConditionalCheckFailedException:
            raise InvalidException('This token has already been claimed')

    @classmethod
    def add_token_index(cls, authorizer: Authorizer) -> int:
        interface = cls.get_interface()
        return interface.update(authorizer.sub, add_to={'generated_token_last': 1},
                                return_values=UpdateReturnValues.UPDATED_NEW)['Attributes']['generated_token_last']

    @classmethod
    def clear_active_task(cls, authorizer: Authorizer,
                          return_values: UpdateReturnValues = UpdateReturnValues.UPDATED_OLD,
                          receive_score=False
                          ):
        interface = cls.get_interface()
        updates = {'target': None}
        add_to = None
        if receive_score:
            beneficiary = BeneficiariesService.get(authorizer.sub, ["target.objective"])

            if beneficiary.target is None:
                return None
            score = 80
            area = split_key(beneficiary.target.objective_key)[1]
            add_to = {
                f'score.{area}': score,
                f'n_tasks.{area}': 1
            }

        try:
            return interface.update(authorizer.sub, updates, None, return_values=return_values,
                                    add_to=add_to, conditions=Attr('target').ne(None))["Attributes"]
        except interface.client.exceptions.ConditionalCheckFailedException:
            raise InvalidException('No active target')

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
            'set_base_tasks': True,
        }
        try:
            return interface.update(authorizer.sub, updates, return_values=UpdateReturnValues.UPDATED_NEW,
                                    conditions=Attr('set_base_tasks').eq(False))
        except interface.client.exceptions.ConditionalCheckFailedException:
            raise InvalidException('Beneficiary already initialized')

    @classmethod
    def get_avatar(cls, user_sub: str):
        interface = cls.get_interface()
        avatar = interface.get(user_sub, attributes=['avatar']).item.get('avatar', {})
        return {
            'left_eye': avatar.get('left_eye'),
            'right_eye': avatar.get('right_eye'),
            "mouth": avatar.get('mouth'),
            "top": avatar.get('top'),
            "bottom": avatar.get('bottom'),
            'neckerchief': avatar.get('neckerchief')
        }

    @classmethod
    def update_avatar(cls, user_sub: str, avatar: dict):
        interface = cls.get_interface()

        item_schema = Or(int, None)
        Schema({
            'left_eye': item_schema,
            'right_eye': item_schema,
            'mouth': item_schema,
            'top': item_schema,
            'bottom': item_schema,
            'neckerchief': item_schema
        }).validate(avatar)
        parts_ids = [part_id for part_id in set(avatar.values()) if part_id is not None]
        if len(parts_ids) > 0:
            logs = LogsService.batch_get(
                [LogKey(sub=user_sub, tag=join_key('REWARD', 'AVATAR', part_id)) for part_id in
                 parts_ids],
                attributes=['data', 'tag'])
            if len(logs) != len(parts_ids):
                raise NotFoundException("An avatar part was not found")
        else:
            logs = []

        avatar_parts = {int(split_key(log.tag)[-1]): Reward.from_api_map(log.data).to_api_map() for log in logs}
        new_avatar = {
            'left_eye': avatar_parts.get(avatar.get('left_eye')),
            'right_eye': avatar_parts.get(avatar.get('right_eye')),
            "mouth": avatar_parts.get(avatar.get('mouth')),
            "top": avatar_parts.get(avatar.get('top')),
            "bottom": avatar_parts.get(avatar.get('bottom')),
            "neckerchief": avatar_parts.get(avatar.get('neckerchief'))
        }
        interface.update(user_sub, updates={'avatar': new_avatar})
        return new_avatar
