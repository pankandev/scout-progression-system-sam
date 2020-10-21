import json
import os
import random
import hashlib

from schema import Schema, SchemaError

from core import db, HTTPEvent, ModelService
from core.auth import CognitoService
from core.aws.errors import HTTPError
from core.aws.response import JSONResponse
from core.utils.key import clean_text, join_key, generate_code, split_key

schema = Schema({
    'district': str,
    'name': str,
})


class UsersCognito(CognitoService):
    __user_pool_id__ = os.environ.get("USER_POOL_ID", "TEST_POOL")


class District(db.Model):
    __table_name__ = "districts"


class GroupsService(ModelService):
    __table_name__ = "groups"
    __partition_key__ = "district"
    __sort_key__ = "code"
    __indices__ = {
        "ByBeneficiaryCode": ("district", "beneficiary-code")
    }

    @staticmethod
    def generate_beneficiary_code(district: str, code: str, group: str):
        h = hashlib.sha1(join_key(district, code).encode()).hexdigest()
        int_hash = (int(h, 16) + random.randint(0, 1024)) % (10 ** 8)
        return join_key(
            f'{int_hash:08}',
            district,
            clean_text(group, remove_spaces=True, lower=True)
        )

    @staticmethod
    def process_beneficiary_code(code: str):
        num, district, group = split_key(code)
        return {
            "district": district,
            "code": num,
            "group": group
        }

    @classmethod
    def create(cls, item: dict, scouter_access_token: str):
        interface = cls.get_interface()
        group = schema.validate(item)
        district = group['district']
        code = generate_code(group['name'])
        group['beneficiary_code'] = cls.generate_beneficiary_code(district, code, group['name'])
        # group['creator_sub'] = UsersCognito.get_user(scouter_access_token).to_dict()

        del group['district']

        interface.create(district, group, code)

    @classmethod
    def get(cls, district: str, code: str):
        interface = cls.get_interface()
        return interface.get(district, code, attributes=["district", "code", "name"])

    @classmethod
    def get_by_code(cls, code: str):
        processed = GroupsService.process_beneficiary_code(code)
        district = processed["district"]

        interface = cls.get_interface("ByBeneficiaryCode")
        return interface.get(district, code, attributes=["district", "code", "name"])

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


def create_group(district: str, item: dict, scouter_access_token: str):
    item["district"] = district
    try:
        GroupsService.create(item, scouter_access_token)
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


def validate_beneficiary_code(event: HTTPEvent):
    code = json.loads(event.body)["code"]
    group = GroupsService.get_by_code(code)
    if group is None:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, "Invalid code")
    return JSONResponse({
        "message": "Code is OK",
        "group": process_group(group, event)
    })


def post_handler(event: HTTPEvent):
    district_code = event.params["district"]

    if event.resource == "/api/groups/validate-code":
        return validate_beneficiary_code(event)
    elif district_code is not None:
        # create group
        if District.get({"code": district_code}).item is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"District '{district_code}' was not found")
        print(event.context)
        return create_group(district_code, json.loads(event.body), "")
    else:
        return JSONResponse.generate_error(HTTPError.UNKNOWN_ERROR, f"Bad resource")


def handler(event, _) -> dict:
    event = HTTPEvent(event)
    if event.method == "GET":
        result = get_handler(event)
    elif event.method == "POST":
        result = post_handler(event)
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")
    return result.as_dict()
