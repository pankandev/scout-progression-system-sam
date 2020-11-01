import time
from typing import List

from schema import Schema

from core import ModelService
from core.aws.event import Authorizer
from core.db.model import Operator, UpdateReturnValues
from core.services.beneficiaries import BeneficiariesService
from core.services.objectives import ObjectivesService
from core.utils import join_key


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

        task = {
            'completed': False,
            'created': int(time.time()),
            'objective': join_key(stage, area, subline),
            'original-objective': objective,
            'personal-objective': description,
            'tasks': [{
                'completed': False,
                'description': description,
            } for description in tasks]
        }

        BeneficiariesService.update(authorizer, active_task=task)
        return task

    @classmethod
    def get_active_task(cls, authorizer: Authorizer):
        return BeneficiariesService.get(authorizer.sub, "target")["target"]

    @classmethod
    def update_active_task(cls, authorizer: Authorizer, description: str, tasks: List[str]):
        return BeneficiariesService.update_active_task(authorizer, description, tasks)["target"]

    @classmethod
    def complete_active_task(cls, authorizer: Authorizer):
        old_active_task = BeneficiariesService.clear_active_task(authorizer,
                                                                 return_values=UpdateReturnValues.UPDATED_OLD)["target"]
        interface = cls.get_interface()
        old_active_task['completed'] = True
        for subtask in old_active_task['tasks']:
            subtask['completed'] = True
        interface.create(authorizer.sub, old_active_task, old_active_task['objective'])
        return old_active_task
