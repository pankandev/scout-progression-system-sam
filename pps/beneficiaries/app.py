from core import HTTPEvent, JSONResponse, ModelService
from core.aws.errors import HTTPError
from core.utils import join_key


class BeneficiariesService(ModelService):
    __table_name__ = "beneficiaries"
    __partition_key__ = "unit"
    __sort_key__ = "code"

    def create(self, district: str, group: str, code: str, name: str):
        pass

    @classmethod
    def get(cls, district: str, group: str, unit: str, code: str):
        interface = cls.get_interface()
        return interface.get(join_key(district, group, unit), code)

    @classmethod
    def query(cls, district: str, group: str, unit: str):
        interface = cls.get_interface()
        return interface.query(join_key(district, group, unit))


def process_beneficiary(beneficiary: dict, event: HTTPEvent):
    try:
        district, group, unit = beneficiary["unit"].split("::")

        beneficiary["district"] = event.concat_url('districts', district)
        beneficiary["group"] = event.concat_url('districts', district, 'groups', group)
        beneficiary["unit"] = event.concat_url('districts', district, 'groups', group, unit)
    except Exception:
        pass


def get_beneficiary(district: str, group: str, unit: str, code: str, event: HTTPEvent):
    result = BeneficiariesService.get(district, group, unit, code)
    process_beneficiary(result.item, event)
    return result


def get_scouts(district: str, group: str, event: HTTPEvent):
    result = BeneficiariesService.query(district, group, "scouts")
    for obj in result.items:
        process_beneficiary(obj, event)
    return result


def get_guides(district: str, group: str, event: HTTPEvent):
    result = BeneficiariesService.query(district, group, "guides")
    for obj in result.items:
        process_beneficiary(obj, event)
    return result


"""Handlers"""


def get_handler(event: HTTPEvent):
    district = event.params["district"]
    group = event.params["group"]
    unit = event.params["unit"]
    code = event.params.get("code")

    if code is None:
        if unit == "scouts":
            result = get_scouts(district, group, event)
        elif unit == "guides":
            result = get_guides(district, group, event)
        else:
            result = JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Unknown unit '{unit}'")
    else:
        result = get_beneficiary(district, group, unit, code, event)
        if result.item is None:
            result = JSONResponse.generate_error(HTTPError.NOT_FOUND, "Beneficiary not found")
    return JSONResponse(result.as_dict())


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)

    if event.method == "GET":
        result = get_handler(event)
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")

    return JSONResponse(result.as_dict()).as_dict()
