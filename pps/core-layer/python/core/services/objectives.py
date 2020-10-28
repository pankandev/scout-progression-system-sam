from core import ModelService
from core.utils import join_key


class ObjectivesService(ModelService):
    __table_name__ = "objectives"
    __partition_key__ = "unit-stage"
    __sort_key__ = "code"

    def create(self, unit: str, stage: str, area: str, line: int, description: str):
        pass

    @classmethod
    def get(cls, unit: str, stage: str, area: str, line: int):
        interface = cls.get_interface()
        return interface.get(join_key(unit, stage), join_key(area, line), attributes=['description'])

    @classmethod
    def query(cls, unit: str, stage: str):
        interface = cls.get_interface()
        return interface.query(join_key(unit, stage))
