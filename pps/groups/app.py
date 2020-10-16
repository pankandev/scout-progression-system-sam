import hashlib
import json
from datetime import datetime

from schema import Schema, SchemaError

from core import db, HTTPEvent, ModelService
from core.aws.errors import HTTPError
from core.aws.response import JSONResponse
from core.utils.key import clean_text, date_to_text, join_key

schema = Schema({
    'district': str,
    'name': str
})


class District(db.Model):
    __table_name__ = "districts"


class GroupsService(ModelService):
    __table_name__ = "groups"
    __partition_key__ = "district"
    __sort_key__ = "code"

    @staticmethod
    def generate_code(date: datetime, name: str):
        name = clean_text(name)
        s_date = date_to_text(date).strip('-')
        return join_key(s_date, name)

    @classmethod
    def create(cls, item: str):
        interface = cls.get_interface()
        group = schema.validate(item)
        district = group['district']
        code = cls.generate_code(datetime.now(), group['name'])
        group['beneficiary_code'] = int(hashlib.sha1(join_key(district, code)).hexdigest(), 16) % (10 ** 8)

        del group['district']

        interface.create(district, code, group)

    @classmethod
    def get(cls, district: str, code: str):
        interface = cls.get_interface()
        return interface.get(district, code, attributes=["district-url", "url", "name"])

    @classmethod
    def query(cls, district: str):
        interface = cls.get_interface()
        return interface.query(district, attributes=["district", "name"])


def process_group(item: dict, event: HTTPEvent):
    try:
        item["district-url"] = event.concat_url("districts", item["district"])
        item["url"] = event.concat_url("districts", item["district"], "groups", item["code"])
    except Exception:
        pass


def create_group(district: str, item: dict):
    item["district"] = district
    try:
        GroupsService.create(item)
    except SchemaError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, f"Item content is invalid: \"{e.code}\"")
    return JSONResponse({"message": "OK"})


def get_handler(event: HTTPEvent):
    district_code = event.params["district"]
    code = event.params.get("group")

    if code is None:
        # get all groups from district
        if District.get({"code": district_code}).item is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"District '{district_code}' was not found")

        response = GroupsService.query(district_code)
        for item in response.items:
            process_group(item, event)
    else:
        # get one group
        response = GroupsService.get(district_code, code)
        if response.item is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Group '{code}' was not found")
        process_group(response.item, event)
    return JSONResponse(response.as_dict())


def post_handler(event: HTTPEvent):
    district_code = event.params["district"]

    if district_code is not None:
        # create group
        if District.get({"code": district_code}).item is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"District '{district_code}' was not found")
        result = create_group(district_code, json.loads(event.body))
    else:
        return JSONResponse.generate_error(HTTPError.UNKNOWN_ERROR, f"Bad resource")
    return JSONResponse(result.as_dict())


def handler(event, _) -> dict:
    event = HTTPEvent(event)
    if event.method == "GET":
        result = get_handler(event)
    elif event.method == "POST":
        result = post_handler(event)
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")
    return result.as_dict()
