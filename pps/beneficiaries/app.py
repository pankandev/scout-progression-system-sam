import json
from datetime import datetime

from botocore.exceptions import ParamValidationError
from schema import Schema

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.services.beneficiaries import BeneficiariesService
from core.services.users import UsersCognito
from core.utils.key import text_to_date

schema = Schema({
    'first_name': str,
    'middle_name': str,
    'family_name': str,
    'nickname': str,
    'birth_date': lambda d: text_to_date(d),
})


def process_beneficiary(beneficiary: dict, event: HTTPEvent):
    try:
        district, group, unit = beneficiary["unit"].split("::")

        beneficiary["district"] = event.concat_url('districts', district)
        beneficiary["group"] = event.concat_url('districts', district, 'groups', group)
        beneficiary["unit"] = event.concat_url('districts', district, 'groups', group, 'beneficiaries', unit)
        beneficiary["stage"] = BeneficiariesService.calculate_stage(
            datetime.strptime(beneficiary["birthdate"], "%d-%m-%Y")
        )
    except Exception:
        pass


def get_beneficiary(district: str, group: str, unit: str, sub: str, event: HTTPEvent):
    result = BeneficiariesService.get(district, group, unit, sub)
    process_beneficiary(result.item, event)
    return result


def get_scouts(district: str, group: str, event: HTTPEvent):
    result = BeneficiariesService.query(district, group, "scouts")
    for obj in result.items:
        process_beneficiary(obj, event)
    return result


def get_guides(district: str, group: str, event: HTTPEvent):
    result = BeneficiariesService.query(district, group, "guides")
    for obj in result.items:
        process_beneficiary(obj, event)
    return result


def signup_beneficiary(event: HTTPEvent):
    data = json.loads(event.body)
    try:
        UsersCognito.sign_up(data['email'], data['password'], {
            'name': data['name'],
            'middle_name': data.get('middle_name'),
            'family_name': data['family_name'],
            'nickname': data.get('nickname'),
            'birthdate': data['birthdate']
        })
    except UsersCognito.get_client().exceptions.UsernameExistsException:
        return JSONResponse.generate_error(HTTPError.EMAIL_ALREADY_IN_USE, "E-mail already in use")
    except UsersCognito.get_client().exceptions.InvalidPasswordException:
        return JSONResponse.generate_error(HTTPError.EMAIL_ALREADY_IN_USE, "Invalid password. Password must have "
                                                                           "uppercase, lowercase, numbers and be at "
                                                                           "least 6 characters long")
    except ParamValidationError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, str(e))

    UsersCognito.add_to_group(data['email'], "Beneficiaries")
    return JSONResponse({"message": "OK"})


"""Handlers"""


def get_handler(event: HTTPEvent):
    district = event.params["district"]
    group = event.params["group"]
    unit = event.params["unit"]
    code = event.params.get("code")

    if unit not in ("scouts", "guides"):
        result = JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Unknown unit '{unit}'")
    elif code is None:
        if unit == "scouts":
            result = get_scouts(district, group, event)
        elif unit == "guides":
            result = get_guides(district, group, event)
        else:
            result = JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Unknown unit '{unit}'")
    else:
        result = get_beneficiary(district, group, unit, code, event)
        if result.item is None:
            result = JSONResponse.generate_error(HTTPError.NOT_FOUND, "Beneficiary not found")
    return JSONResponse(result.as_dict())


def post_handler(event: HTTPEvent):
    if event.resource == "/api/auth/beneficiaries-signup":
        result = signup_beneficiary(event)
    else:
        result = JSONResponse.generate_error(HTTPError.UNKNOWN_ERROR, "Unknown route")
    return result


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)

    if event.method == "GET":
        result = get_handler(event)
    elif event.method == "POST":
        result = post_handler(event)
    else:
        result = JSONResponse.generate_error(HTTPError.NOT_IMPLEMENTED, f"Method {event.method} is not valid")

    return result.as_dict()
