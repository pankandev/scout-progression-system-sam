import json

from botocore.exceptions import ParamValidationError
from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.services.users import UsersCognito


def confirm_user(event: HTTPEvent):
    data = json.loads(event.body)
    try:
        return UsersCognito.confirm(data['email'], data['code'])
    except UsersCognito.get_client().exceptions.UserNotFoundException:
        return JSONResponse.generate_error(HTTPError.UNKNOWN_USER, "User not found")
    except ParamValidationError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, str(e))


def refresh_token(event: HTTPEvent):
    data = json.loads(event.body)
    try:
        token = UsersCognito.refresh(data['token'])
        if token is None:
            return JSONResponse.generate_error(HTTPError.FORBIDDEN, "Invalid credentials")
        return JSONResponse({
            "message": "Refresh successful",
            "token": token.as_dict()
        })
    except UsersCognito.get_client().exceptions.UserNotFoundException:
        return JSONResponse.generate_error(HTTPError.UNKNOWN_USER, "User not found")
    except ParamValidationError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, str(e))


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
        elif event.resource == "/api/auth/refresh":
            result = refresh_token(event)
        else:
            result = JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Resource {event.resource} unknown")
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")
    return result.as_dict()
