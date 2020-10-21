import json
import os

from botocore.exceptions import ParamValidationError

from core import HTTPEvent, JSONResponse, ModelService
from core.auth import CognitoService
from core.aws.errors import HTTPError


class UsersCognito(CognitoService):
    __user_pool_id__ = os.environ.get("USER_POOL_ID", "TEST_POOL")


class GroupsService(ModelService):
    __table_name__ = "groups"
    __partition_key__ = "district"
    __sort_key__ = "code"
    __indices__ = {
        "ByBeneficiaryCode": ("district", "beneficiary-code")
    }

    @classmethod
    def get(cls, district: str, group: str):
        interface = cls.get_interface()
        return interface.get(district, group, attributes=['scouters'])


def process_scouter(scouter: dict, event: HTTPEvent):
    district, group = scouter["group"].split("::")

    scouter["district"] = event.concat_url('districts', district)
    scouter["group"] = event.concat_url('districts', district, 'groups', group)


def get_scouter(district: str, group: str, index: int, event: HTTPEvent):
    result = GroupsService.get(district, group)
    process_scouter(result.item, event)
    return result


def get_scouters(district: str, group: str, event: HTTPEvent):
    result = GroupsService.get(district, group)
    for obj in result.items:
        process_scouter(obj, event)
    return result


def signup_scouter(event: HTTPEvent):
    data = json.loads(event.body)
    try:
        UsersCognito.sign_up(data['email'], data['password'], {
            'name': data['name'],
            'middle_name': data.get('middle_name'),
            'family_name': data['family_name']
        })
    except UsersCognito.get_client().exceptions.UsernameExistsException:
        return JSONResponse.generate_error(HTTPError.EMAIL_ALREADY_IN_USE, "E-mail already in use")
    except ParamValidationError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, str(e))

    UsersCognito.add_to_group(data['email'], "Scouters")
    return JSONResponse({"message": "OK"})


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
    elif event.method == "POST":
        if event.resource == "/api/auth/scouters-signup":
            result = signup_scouter(event)
        else:
            result = JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Resource {event.resource} unknown")
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")

    return result.as_dict()
