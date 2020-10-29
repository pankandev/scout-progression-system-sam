import json
import os

from core.exceptions.notfound import NotFoundException


class ObjectivesService:
    @staticmethod
    def get_stage_objectives(stage):
        this_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(this_path, '../common/objectives', f'{stage}.json')) as f:
            objectives = json.load(f)
        return objectives

    @classmethod
    def get(cls, stage: str, area: str, line: int, sub_line: int):
        objectives = cls.get_stage_objectives(stage)
        if area not in objectives:
            raise NotFoundException(f"Area {area} not found")
        objectives = objectives[area]
        line -= 1
        if line < 0 or line >= len(objectives):
            raise NotFoundException(f"Line {line + 1} on area {area} not found")
        objectives = objectives[line]
        sub_line -= 1
        if sub_line < 0 or sub_line >= len(objectives):
            raise NotFoundException(f"Sub-line {line + 1}.{sub_line + 1} on area {area} not found")
        return objectives[sub_line]

    @classmethod
    def query(cls, stage: str):
        return cls.get_stage_objectives(stage)
