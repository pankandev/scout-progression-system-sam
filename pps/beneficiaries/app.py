import json

from schema import Schema, SchemaError
from datetime import datetime

from core import HTTPEvent, JSONResponse, ModelService
from core.aws.errors import HTTPError
from core.utils import join_key
from core.utils.key import clean_text, text_to_date, date_to_text

schema = Schema({
    'district': str,
    'group': str,
    'unit': str,
    'first_name': str,
    'middle_name': str,
    'last_name': str,
    'second_last_name': str,
    'nickname': str,
    'birth_date': lambda d: text_to_date(d),
})


class BeneficiariesService(ModelService):
    __table_name__ = "beneficiaries"
    __partition_key__ = "unit"
    __sort_key__ = "code"

    @staticmethod
    def generate_code(date: datetime, nick: str):
        nick = clean_text(nick)
        s_date = date_to_text(date).strip('-')
        return join_key(s_date, nick)

    @classmethod
    def create(cls, item: str):
        interface = cls.get_interface()
        beneficiary = schema.validate(item)
        district = beneficiary['district']
        group = beneficiary['group']
        unit = beneficiary['unit']
        del beneficiary['district']
        del beneficiary['group']
        del beneficiary['unit']

        code = cls.generate_code(datetime.now(), beneficiary['nickname'])
        interface.create(join_key(district, group, unit), beneficiary, code)

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
        beneficiary["unit"] = event.concat_url('districts', district, 'groups', group, 'beneficiaries', unit)
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


def create_beneficiary(district: str, group: str, unit: str, item: dict):
    item["district"] = district
    item["group"] = group
    item["unit"] = unit
    try:
        BeneficiariesService.create(item)
    except SchemaError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, f"Item content is invalid: \"{e.code}\"")
    return JSONResponse({"message": "OK"})


"""Handlers"""


def get_handler(event: HTTPEvent):
    district = event.params["district"]
    group = event.params["group"]
    unit = event.params["unit"]
    code = event.params.get("code")

    if unit not in ("scouts", "guides"):
        result = JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Unknown unit '{unit}'")
    elif code is None:
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


def post_handler(event: HTTPEvent):
    district = event.params["district"]
    group = event.params["group"]
    unit = event.params["unit"]
    code = event.params.get("code")

    if unit not in ("scouts", "guides"):
        result = JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Unknown unit '{unit}'")
    elif code is None:
        result = create_beneficiary(district, group, unit, json.loads(event.body))
    else:
        result = JSONResponse.generate_error(HTTPError.UNKNOWN_ERROR, "Unknown route")
    return JSONResponse(result.as_dict())


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)

    if event.method == "GET":
        result = get_handler(event)
    elif event.method == "POST":
        result = post_handler(event)
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")

    return result.as_dict()
