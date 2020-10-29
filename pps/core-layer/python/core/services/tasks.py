from typing import List

from schema import Schema

from core import ModelService
from core.aws.event import Authorizer
from core.services.beneficiaries import BeneficiariesService
from core.services.objectives import ObjectivesService
from core.utils import join_key

schema = Schema({
    'stage': str,
    'objective': {
        'area': str,
        'line': int
    },
    'tasks': [str]
})


class TasksService(ModelService):
    __table_name__ = "objectives"
    __partition_key__ = "user"
    __sort_key__ = "objective-timestamp"

    @classmethod
    def create(cls, stage: str, area: str, line: int, tasks: List[str], description: str, authorizer: Authorizer):
        interface = cls.get_interface()

        objective = ObjectivesService.get(authorizer.unit, stage, area, line)

        task = {
            'objective-description': objective.item['description'],
            'personal-objective': description,
            'completed': False,
            'tasks': [{
                'description': description
            } for description in tasks]
        }

        interface.create(authorizer.sub, task, join_key(authorizer.unit, stage, area, line))

    @classmethod
    def complete(cls, stage: str, area: str, line: int, authorizer: Authorizer):
        interface = cls.get_interface()
        return interface.update(partition_key=authorizer.sub, updates={
            'completed': True
        }, sort_key=join_key(authorizer.unit, stage, area, line), condition_equals={'completed': False})

    @classmethod
    def get(cls, stage: str, area: str, line: int, authorizer: Authorizer):
        interface = cls.get_interface()
        return interface.get(join_key(authorizer.unit, stage), join_key(area, line))

    @classmethod
    def query(cls, authorizer: Authorizer):
        interface = cls.get_interface()
        return interface.query(partition_key=authorizer.sub, attributes=['objective-description', 'completed', 'tasks'])
