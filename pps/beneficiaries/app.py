import json
from datetime import datetime

from core.db.results import QueryResult
from schema import Schema, Optional

from botocore.exceptions import ParamValidationError

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.router.router import Router
from core.services.beneficiaries import BeneficiariesService
from core.services.users import UsersCognito
from core.utils.consts import VALID_UNITS


def process_beneficiary(beneficiary: dict, event: HTTPEvent):
    try:
        district, group, unit = beneficiary["unit"].split("::")

        beneficiary["url"] = event.concat_url('beneficiaries', beneficiary["user-sub"])
        beneficiary["group"] = event.concat_url('districts', district, 'groups', group)
        beneficiary["unit"] = event.concat_url('districts', district, 'groups', group, 'beneficiaries', unit)
        beneficiary["stage"] = BeneficiariesService.calculate_stage(
            datetime.strptime(beneficiary["birthdate"], "%d-%m-%Y")
        )

        del beneficiary["user-sub"]
        del beneficiary["code"]
    except Exception:
        pass


def get_beneficiary(event: HTTPEvent):
    if not event.authorizer.is_scouter and event.authorizer.sub != event.params["sub"]:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You can not access data from this beneficiary")

    result = BeneficiariesService.get(event.params["sub"])
    if result is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, "This user does not have a beneficiaries assigned")

    return JSONResponse(result.to_api_dict(full=True))


def update_beneficiary(event: HTTPEvent):
    if event.authorizer.sub != event.params["sub"]:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You can not access data from this beneficiary")

    result = BeneficiariesService.update(event.authorizer, profile_picture=event.json.get('profile_picture'),
                                         nickname=event.json.get('nickname'))
    if result is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, "This user does not have a beneficiaries assigned")

    return JSONResponse({"message": "Updated successfully"})


def list_beneficiaries_group(event: HTTPEvent):
    district = event.params["district"]
    group = event.params["group"]
    beneficiaries = BeneficiariesService.query_group(district, group)
    return JSONResponse(QueryResult.from_list([b.to_api_dict(full=False) for b in beneficiaries]).as_dict())


def list_beneficiaries_unit(event: HTTPEvent):
    district = event.params["district"]
    group = event.params["group"]
    unit = event.params["unit"]
    if unit not in VALID_UNITS:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Unknown unit: {unit}")

    result = BeneficiariesService.query_unit(district, group, unit)
    result.items = [item.to_api_dict() for item in result.items]
    return JSONResponse(result.as_dict())


def signup_beneficiary(event: HTTPEvent):
    data = json.loads(event.body)
    try:
        attrs = {
            'name': data['name'],
            'family_name': data['family_name'],
            'birthdate': data['birthdate'],
            'gender': data['unit'],
            'nickname': data['nickname']
        }

        try:
            datetime.strptime(attrs["birthdate"], "%d-%m-%Y")
        except ValueError:
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, "Invalid date format, it must match "
                                                                          "%d-%m-%Y format")

        middle_name = data.get('middle_name')
        if middle_name is not None:
            attrs['middle_name'] = middle_name

        UsersCognito.sign_up(data['email'], data['password'], attrs)
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

router = Router()

router.get("/api/districts/{district}/groups/{group}/beneficiaries/{unit}/", list_beneficiaries_unit)
router.get("/api/districts/{district}/groups/{group}/beneficiaries/", list_beneficiaries_group)
router.get("/api/beneficiaries/{sub}/", get_beneficiary)

router.post("/api/auth/beneficiaries-signup/", signup_beneficiary)

router.put("/api/beneficiaries/{sub}/", update_beneficiary, schema=Schema({
    Optional("nickname"): str,
    Optional("profile_picture"): str
}))


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
