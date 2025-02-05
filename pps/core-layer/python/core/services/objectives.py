import json
import math
import os

from core.exceptions.notfound import NotFoundException


class ScoreConfiguration:
    base_score: int
    boost_factor: int
    _instance = None

    def __init__(self, base_score: int, boost_factor: int):
        self.base_score = base_score
        self.boost_factor = boost_factor

    @classmethod
    def instance(cls):
        if cls._instance is not None:
            return cls._instance
        this_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(this_path, '../common/score.json'), encoding='utf-8') as f:
            conf = json.load(f)
        cls._instance = ScoreConfiguration.from_json(conf)
        return cls._instance

    @staticmethod
    def from_json(d: dict):
        return ScoreConfiguration(d["base-score"], d["boost-factor"])


class ObjectivesService:
    @staticmethod
    def get_stage_objectives(stage):
        this_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(this_path, '../common/objectives', f'{stage}.json'), encoding='utf-8') as f:
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

    @classmethod
    def calculate_score_for_task(cls, area: str, n_tasks: dict):
        other_n_tasks = 0
        this_n_tasks = 0
        for area_iter, n_task in n_tasks.items():
            if area_iter == area:
                this_n_tasks += n_tasks[area]
            else:
                other_n_tasks += n_tasks[area]

        conf = ScoreConfiguration.instance()
        boost_factor = conf.boost_factor
        base_score = conf.base_score

        if this_n_tasks == 0:
            this_n_tasks = 0.5
        factor = 1 + other_n_tasks / (5 * this_n_tasks)
        return int(math.ceil(base_score + factor * boost_factor))
