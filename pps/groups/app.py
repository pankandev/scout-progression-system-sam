import json

from schema import SchemaError

from core import db, HTTPEvent
from core.aws.errors import HTTPError
from core.aws.event import Authorizer
from core.aws.response import JSONResponse
from core.services.beneficiaries import BeneficiariesService
from core.services.groups import GroupsService


class District(db.Model):
    __table_name__ = "districts"


def process_group(item: dict, event: HTTPEvent):
    try:
        item["district-url"] = event.concat_url("districts", item["district"])
        item["url"] = event.concat_url("districts", item["district"], "groups", item["code"])
    except Exception:
        pass


def create_group(district: str, item: dict, authorizer: Authorizer):
    try:
        code = item.get('code')
        if code is None:
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, "No code given for new group")
        del item['code']
        GroupsService.create(district, code, item, authorizer.sub, authorizer.full_name)
    except SchemaError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, f"Item content is invalid: \"{e.code}\"")
    return JSONResponse({"message": "OK"})


def join_group(district: str, group: str, code: str, authorizer: Authorizer):

    if not authorizer.is_beneficiary:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "Must be a beneficiary")

    group_item = GroupsService.get(district, group, ["beneficiary_code"]).item
    if group_item is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, "Group not found")
    if group_item["beneficiary_code"] != code:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "Wrong code")
    if BeneficiariesService.create(district, group, authorizer):
        return JSONResponse({"message": "OK"})
    return JSONResponse.generate_error(HTTPError.ALREADY_IN_USE, "You have already joined this group")


def get_handler(event: HTTPEvent):
    district_code = event.params["district"]
    code = event.params.get("group")

    if code is None:
        # get all groups from district
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

    if event.resource == "/api/districts/{district}/groups/{group}/beneficiaries/join":
        # join group
        return join_group(district_code, code, json.loads(event.body)["code"], event.authorizer)
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
