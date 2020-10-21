import json
import os

from botocore.exceptions import ParamValidationError

from core import HTTPEvent, JSONResponse
from core.auth import CognitoService
from core.aws.errors import HTTPError


class UsersCognito(CognitoService):
    __user_pool_id__ = os.environ.get("USER_POOL_ID", "TEST_POOL")


def confirm_user(event: HTTPEvent):
    data = json.loads(event.body)
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
    except ParamValidationError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, e.message)


"""Handlers"""


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)

    if event.method == "POST":
        if event.resource == "/api/users/login":
            result = login(event)
        elif event.resource == "/api/users/confirm":
            result = confirm_user(event)
        else:
            result = JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Resource {event.resource} unknown")
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")

    return result.as_dict()
