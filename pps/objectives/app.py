from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.services.objectives import ObjectivesService
from core.utils.consts import VALID_UNITS, VALID_STAGES, VALID_AREAS


def process_objective(objective: dict):
    unit, stage = objective["unit-stage"].split("::")
    del objective["unit-stage"]

    area, line = objective["code"].split("::")

    objective["unit"] = unit
    objective["stage"] = stage
    objective["area"] = area
    objective["line"] = int(line)


def get_objective(stage: str, area: str, line: int, sub_line: int):
    result = ObjectivesService.get(stage, area, line, sub_line)
    process_objective(result.item)
    return result


def get_objectives(stage: str):
    result = ObjectivesService.query(stage)
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
    line = event.params.get("line")
    if area is None and line is None:
        # get all objectives from unit and stage
        response = get_objectives(stage)
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
