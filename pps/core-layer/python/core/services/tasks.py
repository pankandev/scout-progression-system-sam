import time
from typing import List, Union

from boto3.dynamodb.conditions import Attr

from core import ModelService
from core.aws.event import Authorizer
from core.db.model import Operator, UpdateReturnValues
from core.db.results import GetResult
from core.services.beneficiaries import BeneficiariesService
from core.services.objectives import ObjectivesService
from core.utils import join_key


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

    def __init__(self, description: str, completed: str):
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
    tasks: List[Subtask]

    def __init__(self, created: int, completed: str, objective_key: str, original_objective: str,
                 personal_objective: str, tasks: List[Subtask]):
        self.created = created
        self.completed = completed
        self.objective_key = objective_key
        self.original_objective = original_objective
        self.personal_objective = personal_objective
        self.tasks = tasks

    @staticmethod
    def from_db_dict(d: dict):
        return Task(d["created"], d["completed"], d["objective"], d["original-objective"], d["personal-objective"],
                    [Subtask.from_dict(c) for c in d["tasks"]])

    def to_dict(self):
        return {
            'completed': False,
            'created': int(time.time()),
            'objective': self.objective_key,
            'original-objective': self.original_objective,
            'personal-objective': self.personal_objective,
            'tasks': [{
                'completed': False,
                'description': task.description,
            } for task in self.tasks]
        }


class TasksService(ModelService):
    __table_name__ = "tasks"
    __partition_key__ = "user"
    __sort_key__ = "objective"

    @classmethod
    def get(cls, authorizer: Authorizer, stage: str, area: str, subline: int):
        interface = cls.get_interface()
        return interface.get(authorizer.sub, join_key(stage, area, subline))

    @classmethod
    def query(cls, authorizer: Authorizer, stage: str = None, area: str = None):
        interface = cls.get_interface()
        args = [arg for arg in (stage, area) if arg is not None]
        sort_key = (Operator.BEGINS_WITH, join_key(*args, '')) if len(args) > 0 else None
        return interface.query(partition_key=authorizer.sub, sort_key=sort_key,
                               attributes=['objective-description', 'completed', 'tasks'])

    """Active Task methods"""

    @classmethod
    def start_task(cls, authorizer: Authorizer, stage: str, area: str, subline: str, tasks: List[str],
                   description: str):
        line_, subline_ = subline.split('.')
        objective = ObjectivesService.get(stage, area, int(line_), int(subline_))

        task = Task(
            created=int(time.time()),
            completed=False,
            objective_key=join_key(stage, area, subline),
            original_objective=objective,
            personal_objective=description,
            tasks=[Subtask(completed=False, description=description) for description in tasks]
        )

        try:
            BeneficiariesService.update(authorizer, active_task=task.to_dict())
        except BeneficiariesService.exceptions().ConditionalCheckFailedException:
            return None
        return task

    @classmethod
    def get_active_task(cls, authorizer: Authorizer) -> Union[Task, None]:
        return GetResult.from_item(BeneficiariesService.get(authorizer.sub, ["target"]).item["target"])

    @classmethod
    def update_active_task(cls, authorizer: Authorizer, description: str, tasks: List[str]) -> Union[Task, None]:
        return BeneficiariesService.update_active_task(authorizer, description, tasks)["target"]

    @classmethod
    def dismiss_active_task(cls, authorizer: Authorizer):
        return BeneficiariesService.clear_active_task(authorizer)["target"]

    @classmethod
    def complete_active_task(cls, authorizer: Authorizer):
        old_active_task = BeneficiariesService.clear_active_task(authorizer,
                                                                 return_values=UpdateReturnValues.UPDATED_OLD,
                                                                 receive_score=True)["target"]
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
        cls._add_objectives_as_completed(authorizer, objectives)
        BeneficiariesService.mark_as_initialized(authorizer=authorizer)

    @classmethod
    def _add_objectives_as_completed(cls, authorizer: Authorizer, objectives: List[ObjectiveKey]):
        # noinspection PyProtectedMember
        model = cls.get_interface()._model
        client = model.get_table().meta.client
        now = int(time.time())
        request_items = {
            model.__table_name__: [
                {
                    'PutRequest': {
                        'Item': {
                            'completed': {'BOOL': True, },
                            'created': {'N': now, },
                            'objective': {'S': join_key(authorizer.stage, key.area, f'{key.line}.{key.subline}'), },
                            'original-objective': {
                                'S': ObjectivesService.get(authorizer.stage, key.area, key.line, key.subline), },
                            'personal-objective': {'NULL': True},
                            'score': {'N': 0},
                            'tasks': {'NULL': True},
                            'user': {'S': authorizer.sub}
                        },
                    }
                } for key in objectives]
        }
        client.batch_write_item(
            RequestItems=request_items
        )
