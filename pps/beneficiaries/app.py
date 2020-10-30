import json
from datetime import datetime

from botocore.exceptions import ParamValidationError

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.services.beneficiaries import BeneficiariesService
from core.services.users import UsersCognito
from core.utils.consts import VALID_UNITS


def process_beneficiary(beneficiary: dict, event: HTTPEvent):
    try:
        district, group, unit = beneficiary["unit"].split("::")

        beneficiary["district"] = event.concat_url('districts', district)
        beneficiary["url"] = event.concat_url('districts', district, 'groups', group, 'beneficiaries', unit,
                                              beneficiary["user-sub"])
        beneficiary["group"] = event.concat_url('districts', district, 'groups', group)
        beneficiary["unit"] = event.concat_url('districts', district, 'groups', group, 'beneficiaries', unit)
        beneficiary["stage"] = BeneficiariesService.calculate_stage(
            datetime.strptime(beneficiary["birthdate"], "%d-%m-%Y")
        )

        del beneficiary["user-sub"]
        del beneficiary["code"]
    except Exception:
        pass


def get_beneficiary(district: str, group: str, unit: str, sub: str, event: HTTPEvent):
    result = BeneficiariesService.get(district, group, unit, sub)
    process_beneficiary(result.item, event)
    return result


def get_group(district: str, group: str, event: HTTPEvent):
    result = BeneficiariesService.query_group(district, group)
    for obj in result.items:
        process_beneficiary(obj, event)
    return result


def get_unit(district: str, group: str, unit: str, event: HTTPEvent):
    result = BeneficiariesService.query_unit(district, group, unit)
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
            'birthdate': data['birthdate'],
            'gender': data['unit'],
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
    unit = event.params.get("unit")
    code = event.params.get("code")

    if unit is None:
        # get all beneficiaries from group
        return JSONResponse(get_group(district, group, event).as_dict())

    if unit not in VALID_UNITS:
        # unknown unit
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Unknown unit '{unit}'")

    if code is None:
        # get all beneficiaries from a unit in a group
        return JSONResponse(get_unit(district, group, unit, event).as_dict())

    # get one beneficiary
    result = get_beneficiary(district, group, unit, code, event)
    if result.item is None:
        # beneficiary not found
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, "Beneficiary not found")
    return result


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
