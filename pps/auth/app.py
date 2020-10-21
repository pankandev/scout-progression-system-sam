import json
import os

from botocore.exceptions import ParamValidationError

from core import HTTPEvent, JSONResponse, ModelService
from core.auth import CognitoService
from core.aws.errors import HTTPError
from core.utils.key import split_key


class UsersCognito(CognitoService):
    __user_pool_id__ = os.environ.get("USER_POOL_ID", "TEST_POOL")


class GroupsService(ModelService):
    __table_name__ = "groups"
    __partition_key__ = "district"
    __sort_key__ = "code"
    __indices__ = {
        "ByBeneficiaryCode": ("district", "beneficiary-code")
    }

    @staticmethod
    def process_beneficiary_code(code: str):
        num, district, group = split_key(code)
        return {
            "district": district,
            "code": num,
            "group": group
        }

    @classmethod
    def get_by_code(cls, code: str):
        processed = GroupsService.process_beneficiary_code(code)
        district = processed["district"]

        interface = cls.get_interface("ByBeneficiaryCode")
        return interface.get(district, code, attributes=["district", "code", "name"])


def process_group(item: dict, event: HTTPEvent):
    try:
        item["district-url"] = event.concat_url("districts", item["district"])
        item["url"] = event.concat_url("districts", item["district"], "groups", item["code"])
    except Exception:
        pass


def validate_beneficiary_code(event: HTTPEvent):
    code = json.loads(event.body)["code"]
    group = GroupsService.get_by_code(code)
    if group is None:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, "Invalid code")
    return JSONResponse({
        "message": "Code is OK",
        "group": process_group(group, event)
    })


def confirm_user(event: HTTPEvent):
    data = json.loads(event.body)
    print(event.context)
    try:
        return UsersCognito.confirm(data['email'], data['code'])
    except ParamValidationError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, e.message)


def login(event: HTTPEvent):
    data = json.loads(event.body)
    try:
        token = UsersCognito.log_in(data['email'], data['password'])
        if token is None:
            return JSONResponse.generate_error(HTTPError.FORBIDDEN, "Invalid credentials")
        return JSONResponse({
            "message": "Log-in successful",
            "token": token.as_dict()
        })
    except UsersCognito.get_client().exceptions.UserNotConfirmedException:
        return JSONResponse.generate_error(HTTPError.UNCONFIRMED_USER, "User is unconfirmed, check your e-mail for "
                                                                       "the confirmation code.")
    except ParamValidationError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, e.message)


"""Handlers"""


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)

    if event.method == "POST":
        if event.resource == "/api/auth/login":
            result = login(event)
        elif event.resource == "/api/auth/confirm":
            result = confirm_user(event)
        elif event.resource == "/api/auth/validate-beneficiary-code":
            result = validate_beneficiary_code(event)
        else:
            result = JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Resource {event.resource} unknown")
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")

    return result.as_dict()
