from core import HTTPEvent, JSONResponse, ModelService
from core.aws.errors import HTTPError
from core.utils import join_key


class ScoutersService(ModelService):
    __table_name__ = "scouters"
    __partition_key__ = "group"
    __sort_key__ = "code"

    def create(self, district: str, group: str, code: str, name: str):
        pass

    @classmethod
    def get(cls, district: str, group: str, code: str):
        interface = cls.get_interface()
        return interface.get(join_key(district, group), code)

    @classmethod
    def query(cls, district: str, group: str):
        interface = cls.get_interface()
        return interface.query(join_key(district, group))


def process_scouter(scouter: dict, event: HTTPEvent):
    district, group = scouter["group"].split("::")

    scouter["district"] = event.concat_url('districts', district)
    scouter["group"] = event.concat_url('districts', district, 'groups', group)


def get_scouter(district: str, group: str, code: str, event: HTTPEvent):
    result = ScoutersService.get(district, group, code)
    process_scouter(result.item, event)
    return result


def get_scouters(district: str, group: str, event: HTTPEvent):
    result = ScoutersService.query(district, group)
    for obj in result.items:
        process_scouter(obj, event)
    return result


"""Handlers"""


def get_handler(event: HTTPEvent):
    district = event.params["district"]
    group = event.params["group"]
    code = event.params.get("code")

    if code is None:
        result = get_scouters(district, group, event)
    else:
        result = get_scouter(district, group, code, event)
        if result.item is None:
            result = JSONResponse.generate_error(HTTPError.NOT_FOUND, "Scouter not found")
    return JSONResponse(result.as_dict())


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)

    if event.method == "GET":
        result = get_handler(event)
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")

    return JSONResponse(result.as_dict()).as_dict()
