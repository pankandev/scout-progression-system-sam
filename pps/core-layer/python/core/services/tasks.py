import json
import math
import os
import time
from datetime import timedelta, datetime, timezone
from typing import List, Union, Optional

import jwt
from core import ModelService
from core.aws.event import Authorizer
from core.db.model import Operator, UpdateReturnValues
from core.db.results import GetResult, QueryResult
from core.exceptions.forbidden import ForbiddenException
from core.exceptions.invalid import InvalidException
from core.exceptions.notfound import NotFoundException
from core.services.objectives import ObjectivesService, ScoreConfiguration
from core.services.rewards import RewardsFactory, RewardReason
from core.utils import join_key
from core.utils.key import split_key
from jwt.utils import get_int_from_datetime
from schema import Schema, SchemaError


class ObjectiveKey:
    area: str
    line: int
    subline: int

    def __init__(self, area: str, line: int, subline: int):
        self.area = area
        self.line = line
        self.subline = subline

    def __eq__(self, other):
        return other.line == self.line and other.subline == self.subline and other.area == self.area


class Subtask:
    description: str
    completed: bool

    def __init__(self, description: str, completed: bool):
        self.description = description
        self.completed = completed

    @staticmethod
    def from_dict(d: dict):
        return Subtask(d["description"], d["completed"])

    def to_dict(self):
        return {
            "description": self.description,
            "completed": self.completed
        }


class Task:
    completed: bool
    created: int
    objective_key: str
    original_objective: str
    personal_objective: str
    score: int
    tasks: List[Subtask]

    def __init__(self, created: int, completed: str, objective_key: str, original_objective: str,
                 personal_objective: str, tasks: List[Subtask], score: Optional[int] = None):
        self.created = created
        self.completed = completed
        self.objective_key = objective_key
        self.original_objective = original_objective
        self.personal_objective = personal_objective
        self.tasks = tasks
        self.score = int(score) if score is not None else ScoreConfiguration.instance().base_score

    @staticmethod
    def from_db_dict(d: dict):
        return Task(d.get("created"),
                    d.get("completed"),
                    d.get("objective"),
                    d.get("original-objective"),
                    d.get("personal-objective"), [Subtask.from_dict(c) for c in d.get("tasks", [])],
                    d.get('score'))

    def to_db_dict(self):
        return {
            'completed': False,
            'created': self.created,
            'objective': self.objective_key,
            'score': self.score,
            'original-objective': self.original_objective,
            'personal-objective': self.personal_objective,
            'tasks': [{
                'completed': task.completed,
                'description': task.description,
            } for task in self.tasks]
        }

    def to_api_dict(self, authorizer: Authorizer = None):
        data = {
            'completed': self.completed,
            'created': int(time.time()),
            'objective': self.objective_key,
            'stage': split_key(self.objective_key)[0],
            'area': split_key(self.objective_key)[1],
            'score': self.score,
            'line': int(split_key(self.objective_key)[2].split('.')[0]),
            'subline': int(split_key(self.objective_key)[2].split('.')[1]),
            'original-objective': self.original_objective,
            'personal-objective': self.personal_objective,
            'tasks': [{
                'completed': task.completed,
                'description': task.description,
            } for task in self.tasks],
        }
        if authorizer is not None:
            data['token'] = self.generate_token(authorizer, duration=timedelta(days=1))
        return data

    def generate_token(self, authorizer: Authorizer, duration: timedelta = None):
        return Task.generate_objective_token(self.objective_key, authorizer=authorizer, duration=duration)

    @classmethod
    def generate_objective_token(cls, objective_key: str, authorizer: Authorizer, duration: timedelta = None):
        if duration is None:
            duration = timedelta(days=1)
        jwk_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'jwk.json')
        with open(jwk_path, 'r') as f:
            jwk = jwt.jwk_from_dict(json.load(f))
        encoder = jwt.JWT()

        now = datetime.now(timezone.utc)
        payload = {
            'sub': authorizer.sub,
            "iat": get_int_from_datetime(now),
            "exp": get_int_from_datetime(now + duration),
            "objective": objective_key
        }
        return encoder.encode(payload, jwk)


class TasksService(ModelService):
    __table_name__ = "tasks"
    __partition_key__ = "user"
    __sort_key__ = "objective"

    @classmethod
    def get(cls, authorizer: Authorizer, stage: str, area: str, subline: int) -> Task:
        interface = cls.get_interface()
        item = interface.get(authorizer.sub, join_key(stage, area, subline)).item
        if item is None:
            raise NotFoundException('Task not found')
        return Task.from_db_dict(item)

    @classmethod
    def query(cls, authorizer: Authorizer, stage: str = None, area: str = None):
        interface = cls.get_interface()
        args = [arg for arg in (stage, area) if arg is not None]
        sort_key = (Operator.BEGINS_WITH, join_key(*args, '')) if len(args) > 0 else None
        return QueryResult.from_list(
            [
                Task.from_db_dict(item) for item in interface.query(partition_key=authorizer.sub, sort_key=sort_key,
                                                                    attributes=['objective', 'original-objective',
                                                                                'personal-objective',
                                                                                'completed',
                                                                                'tasks', 'user']).items
            ])

    """Active Task methods"""

    @classmethod
    def start_task(cls, authorizer: Authorizer, stage: str, area: str, subline: str, tasks: List[str],
                   description: str):
        from core.services.beneficiaries import BeneficiariesService
        line_, subline_ = subline.split('.')
        objective = ObjectivesService.get(stage, area, int(line_), int(subline_))

        now = datetime.now(timezone.utc)
        task = Task(
            created=int(now.timestamp() * 1000),
            completed=False,
            objective_key=join_key(stage, area, subline),
            original_objective=objective,
            personal_objective=description,
            tasks=[Subtask(completed=False, description=description) for description in tasks]
        )

        try:
            BeneficiariesService.update(authorizer, active_task=task.to_db_dict())
        except BeneficiariesService.exceptions().ConditionalCheckFailedException:
            return None
        return task

    @classmethod
    def get_active_task(cls, authorizer: Authorizer) -> Union[GetResult, None]:
        from core.services.beneficiaries import BeneficiariesService
        beneficiary = BeneficiariesService.get(authorizer.sub, ["target"])

        target = beneficiary.target
        if target is None:
            raise NotFoundException('Task not found')

        target_dict = target.to_api_dict(authorizer=authorizer) if target is not None else None
        return GetResult.from_item(target_dict)

    @classmethod
    def get_task_token_objective(cls, token: str, authorizer: Authorizer) -> str:
        jwk_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'jwk.json')
        with open(jwk_path, 'r') as f:
            jwk = jwt.jwk_from_dict(json.load(f))
        decoded = jwt.JWT().decode(token, jwk)
        try:
            Schema({
                "sub": str,
                "objective": str,
                "exp": int,
                "iat": int
            }).validate(decoded)
        except SchemaError:
            raise InvalidException("The given task token is not valid")
        if authorizer.sub != decoded['sub']:
            raise ForbiddenException("The given task token does not belong to this user")
        return decoded['objective']

    @classmethod
    def update_active_task(cls, authorizer: Authorizer, description: str, tasks: List[str]) -> Union[Task, None]:
        from core.services.beneficiaries import BeneficiariesService
        return BeneficiariesService.update_active_task(authorizer, description, tasks)["target"]

    @classmethod
    def dismiss_active_task(cls, authorizer: Authorizer):
        from core.services.beneficiaries import BeneficiariesService
        return BeneficiariesService.clear_active_task(authorizer, return_values=UpdateReturnValues.UPDATED_OLD).get(
            "target")

    @classmethod
    def complete_active_task(cls, authorizer: Authorizer):
        from core.services.beneficiaries import BeneficiariesService
        old_active_task = BeneficiariesService.clear_active_task(authorizer,
                                                                 return_values=UpdateReturnValues.UPDATED_OLD,
                                                                 receive_score=True).get("target")
        if old_active_task is None:
            return None

        interface = cls.get_interface()
        old_active_task['completed'] = True
        for subtask in old_active_task['tasks']:
            subtask['completed'] = True
        interface.create(authorizer.sub, old_active_task, old_active_task['objective'])
        return old_active_task

    @classmethod
    def initialize(cls, authorizer: Authorizer, objectives: List[ObjectiveKey]):
        from core.services.beneficiaries import BeneficiariesService
        cls._add_objectives_as_completed(authorizer, objectives)
        BeneficiariesService.mark_as_initialized(authorizer=authorizer)
        return RewardsFactory.get_reward_token_by_reason(authorizer=authorizer, reason=RewardReason.INITIALIZE)

    @classmethod
    def _add_objectives_as_completed(cls, authorizer: Authorizer, objectives: List[ObjectiveKey]):
        # noinspection PyProtectedMember
        model = cls.get_interface()._model
        client = model.get_table().meta.client
        now = datetime.now(timezone.utc)
        now = int(now.timestamp() * 1000)
        n_chunks = math.ceil(len(objectives) / 25)
        # do batch writes in chunks of 25 to avoid errors
        for i_chunk in range(n_chunks):
            start = i_chunk * 25
            end = min((i_chunk + 1) * 25, len(objectives))
            chunk = objectives[start:end]
            request_items = {
                model.__table_name__: [
                    {
                        'PutRequest': {
                            'Item': {
                                'completed': True,
                                'created': now,
                                'objective': join_key(authorizer.stage, key.area, f'{key.line}.{key.subline}'),
                                'original-objective': ObjectivesService.get(authorizer.stage, key.area, key.line,
                                                                            key.subline),
                                'personal-objective': None,
                                'score': 0,
                                'tasks': [],
                                'user': authorizer.sub
                            },
                        }
                    } for key in chunk]
            }
            client.batch_write_item(
                RequestItems=request_items
            )
