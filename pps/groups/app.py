import json
import os

from core.exceptions.invalid import InvalidException
from core.router.router import Router
from schema import SchemaError, Schema

from core import db, HTTPEvent
from core.auth import CognitoService
from core.aws.errors import HTTPError
from core.aws.event import Authorizer
from core.aws.response import JSONResponse
from core.services.beneficiaries import BeneficiariesService
from core.services.groups import GroupsService


class District(db.Model):
    __table_name__ = "districts"


class UsersCognito(CognitoService):
    __user_pool_id__ = os.environ.get("USER_POOL_ID", "TEST_POOL")


def process_group(item: dict, event: HTTPEvent):
    try:
        item["district-url"] = event.concat_url("districts", item["district"])
        item["url"] = event.concat_url("districts", item["district"], "groups", item["code"])
    except Exception:
        pass


def create_group(event: HTTPEvent):
    district = event.params["district"]
    item = event.json
    Schema({
        'code': str,
        'name': str
    }).validate(item)
    code = item['code']
    try:
        del item['code']
        GroupsService.create(district, code, item, event.authorizer.sub, event.authorizer.full_name)
    except GroupsService.exceptions().ConditionalCheckFailedException:
        raise InvalidException(f"Group in district {district} with code {code} already exists")
    except SchemaError as e:
        raise InvalidException(f"Item content is invalid: \"{e.code}\"")
    return JSONResponse({"message": "OK"})


def join_group(event: HTTPEvent):
    district = event.params["district"]
    group = event.params["group"]
    code = event.json["code"]
    print(os.environ["USER_POOL_ID"])
    if not event.authorizer.is_beneficiary:
        UsersCognito.add_to_group(event.authorizer.username, "Beneficiaries")
    group_item = GroupsService.get(district, group, ["beneficiary_code"]).item
    if group_item is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, "Group not found")
    if group_item["beneficiary_code"] != code:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "Wrong code")
    BeneficiariesService.create(district, group, event.authorizer)
    return JSONResponse({"message": "OK"})


def list_groups(event: HTTPEvent):
    district_code = event.params["district"]
    response = GroupsService.query(district_code)
    for item in response.items:
        process_group(item, event)
    return JSONResponse(response.as_dict())


def get_group(event: HTTPEvent):
    district_code = event.params["district"]
    code = event.params["group"]
    response = GroupsService.get(district_code, code,
                                 attributes=["district", "code", "name", "beneficiary_code", "scouters_code",
                                             "scouters"])
    if response.item is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Group '{code}' was not found")
    if event.authorizer.sub not in response.item['scouters'].keys():
        del response.item['scouters']
        del response.item['beneficiary_code']
        del response.item['scouters_code']
    process_group(response.item, event)
    return JSONResponse(response.as_dict())


router = Router()
router.get("/api/districts/{district}/groups/", list_groups)
router.get("/api/districts/{district}/groups/{group}/", get_group)

router.post("/api/districts/{district}/groups/", create_group)
router.post("/api/districts/{district}/groups/{group}/beneficiaries/join", join_group)


def handler(event, _) -> dict:
    event = HTTPEvent(event)
    result = router.route(event)
    return result.as_dict()
