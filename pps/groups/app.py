import json
import os
import random
import hashlib
from datetime import datetime

import botocore
from schema import Schema, SchemaError

from core import db, HTTPEvent, ModelService
from core.auth import CognitoService
from core.aws.errors import HTTPError
from core.aws.event import Authorizer
from core.aws.response import JSONResponse
from core.utils.key import clean_text, join_key, generate_code, split_key, date_to_text

schema = Schema({
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

    @staticmethod
    def generate_beneficiary_code(district: str, group_code: str):
        h = hashlib.sha1(join_key(district, group_code).encode()).hexdigest()
        int_hash = (int(h, 16) + random.randint(0, 1024)) % (10 ** 8)
        return f'{int_hash:08}'

    @staticmethod
    def process_beneficiary_code(code: str):
        num, district, group = split_key(code)
        return {
            "district": district,
            "code": num,
            "group": group
        }

    @classmethod
    def create(cls, district: str, item: dict, creator_sub: str, creator_full_name: str):
        interface = cls.get_interface()
        group = schema.validate(item)
        code = generate_code(group['name'])
        group['beneficiary_code'] = cls.generate_beneficiary_code(district, code)
        group['creator'] = {
            "sub": creator_sub,
            "name": creator_full_name
        }
        group['scouters'] = list()

        interface.create(district, group, code)

    @classmethod
    def get(cls, district: str, code: str, attributes: list = None):
        if attributes is None:
            attributes = ["district", "code", "name"]

        interface = cls.get_interface()
        return interface.get(district, code, attributes=attributes)

    @classmethod
    def query(cls, district: str):
        interface = cls.get_interface()
        return interface.query(district, attributes=["district", "name", "code"])


class BeneficiariesService(ModelService):
    __table_name__ = "beneficiaries"
    __partition_key__ = "unit"
    __sort_key__ = "code"

    @staticmethod
    def generate_code(date: datetime, nick: str):
        nick = clean_text(nick, remove_spaces=True, lower=True)
        s_date = date_to_text(date).replace('-', '')
        return join_key(nick, s_date).replace('::', '')

    @classmethod
    def create(cls, district: str, group: str, unit: str, authorizer: Authorizer):
        interface = cls.get_interface()

        code = cls.generate_code(datetime.now(), authorizer.full_name)
        beneficiary = {
            "sub": authorizer.sub,
            "full-name": authorizer.full_name,
            "nickname": authorizer.nickname,
            "tasks": []
        }
        try:
            interface.create(join_key(district, group, unit), beneficiary, code, raise_if_exists=True,
                             raise_attribute_equals={"sub": authorizer.sub})
            return True
        except botocore.exceptions.ClientError as e:
            print(e)
            print(str(e))
            return False


def process_group(item: dict, event: HTTPEvent):
    try:
        item["district-url"] = event.concat_url("districts", item["district"])
        item["url"] = event.concat_url("districts", item["district"], "groups", item["code"])
    except Exception:
        pass


def create_group(district: str, item: dict, authorizer: Authorizer):
    try:
        GroupsService.create(district, item, authorizer.sub, authorizer.full_name)
    except SchemaError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, f"Item content is invalid: \"{e.code}\"")
    return JSONResponse({"message": "OK"})


def join_group(district: str, group: str, unit: str, code: str, authorizer: Authorizer):
    group_item = GroupsService.get(district, group, ["beneficiary_code"]).item
    if group_item["beneficiary_code"] != code:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "Wrong code")
    if BeneficiariesService.create(district, group, unit, authorizer):
        return JSONResponse({"message": "OK"})
    return JSONResponse.generate_error(HTTPError.ALREADY_IN_USE, "You have already joined this group")


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
    code = event.params.get("group")
    unit = event.params.get("unit")

    if event.resource == "/api/districts/{district}/groups/{group}/beneficiaries/{unit}/join":
        # join group
        return join_group(district_code, code, unit, json.loads(event.body)["code"], event.authorizer)
    elif district_code is not None:
        # create group
        if District.get({"code": district_code}).item is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"District '{district_code}' was not found")
        return create_group(district_code, json.loads(event.body), event.authorizer)
    else:
        # unknown resource
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
