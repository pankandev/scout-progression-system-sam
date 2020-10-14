from core import HTTPEvent, JSONResponse, ModelService
from core.aws.errors import HTTPError


def join_key(*args):
    return '::'.join(args)


class ObjectivesService(ModelService):
    __table_name__ = "objectives"

    def create(self, unit: str, stage: str, area: str, line: int, description: str):
        pass

    @classmethod
    def get(cls, unit: str, stage: str, area: str, line: int):
        interface = cls.get_interface()
        return interface.get(join_key(unit, stage), join_key(area, line))

    @classmethod
    def query(cls, unit: str, stage: str):
        interface = cls.get_interface()
        return interface.query(join_key(unit, stage))


VALID_UNITS = ["guides", "scouts"]
VALID_STAGES = ["prepuberty", "puberty"]
VALID_AREAS = [
    "corporality",
    "creativity",
    "character",
    "affectivity",
    "sociability",
    "spirituality"
]


def process_objective(objective: dict):
    unit, stage = objective["unit-stage"].split("::")
    del objective["unit-stage"]

    area, line = objective["code"].split("::")

    objective["unit"] = unit
    objective["stage"] = stage
    objective["area"] = area
    objective["line"] = int(line)


def get_objective(unit: str, stage: str, area: str, line: int):
    result = ObjectivesService.get(unit, stage, area, line)
    process_objective(result.item)
    return result


def get_objectives(unit: str, stage: str):
    result = ObjectivesService.query(unit, stage)
    for obj in result.items:
        process_objective(obj)
    return result


def get_handler(event: HTTPEvent) -> JSONResponse:

    # validate unit
    unit = event.params.get("unit").lower()
    if unit not in VALID_UNITS:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND,
                                           f"Unit '{unit}' is not valid")

    # validate stage
    stage = event.params.get("stage").lower()
    if stage not in VALID_STAGES:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND,
                                           f"Stage '{stage}' not found")

    area = event.params.get("area")
    line = event.params.get("unit")
    if area is None and line is None:
        # get all objectives from unit and stage
        response = get_objectives(unit, stage)
    else:
        # get one objective
        area = area.lower()
        if area not in VALID_AREAS:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND,
                                               f"Area '{area}' not found")

        try:
            line = int(line)
        except ValueError:
            return JSONResponse.generate_error(HTTPError.INVALID_ID,
                                               f"Given line ID '{line}' is not a number")

        response = get_objective(unit, stage, area, line)
        if response.item is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND,
                                               f"Could not find '{area}' objective with line {line}")
        process_objective(response.item)
    return JSONResponse(response.as_dict())


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    return get_handler(event).as_dict()
