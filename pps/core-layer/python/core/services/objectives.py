from core import ModelService
from core.utils import join_key


class ObjectivesService(ModelService):
    __table_name__ = "objectives"
    __partition_key__ = "area"
    __sort_key__ = "subline"

    def create(self, unit: str, stage: str, area: str, line: int, sub_line: int, description: str):
        pass

    @classmethod
    def get(cls, stage: str, area: str, line: int, sub_line: int):
        interface = cls.get_interface()
        return interface.get(stage, join_key(area, line, sub_line), attributes=['description'])

    @classmethod
    def query(cls, stage: str):
        interface = cls.get_interface()
        return interface.query(stage)
