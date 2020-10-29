import json
import os

from botocore.exceptions import ParamValidationError

from core import HTTPEvent, JSONResponse
from core.auth import CognitoService
from core.aws.errors import HTTPError
from core.services.groups import GroupsService


class UsersCognito(CognitoService):
    __user_pool_id__ = os.environ.get("USER_POOL_ID", "TEST_POOL")


def process_scouter(scouter: dict, event: HTTPEvent):
    district, group = scouter["group"].split("::")

    scouter["district"] = event.concat_url('districts', district)
    scouter["group"] = event.concat_url('districts', district, 'groups', group)


def get_scouter(district: str, group: str, sub: int, event: HTTPEvent):
    scouters = GroupsService.get(district, group, attributes=['scouters']).item['scouters']
    scouter = scouters[sub]
    process_scouter(scouter, event)
    return scouter


def get_scouters(district: str, group: str, event: HTTPEvent):
    result = GroupsService.get(district, group, attributes=['scouters'])
    for obj in result.items:
        process_scouter(obj, event)
    return result.items


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
    except UsersCognito.get_client().exceptions.InvalidPasswordException:
        return JSONResponse.generate_error(HTTPError.EMAIL_ALREADY_IN_USE, "Invalid password. Password must have "
                                                                           "uppercase, lowercase, numbers and be at "
                                                                           "least 6 characters long")
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
        if result is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, "Scouter not found")
    return JSONResponse(result)


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
