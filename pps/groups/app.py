import os
from typing import List, Dict

from core import db, HTTPEvent
from core.auth import CognitoService
from core.aws.errors import HTTPError
from core.aws.response import JSONResponse
from core.exceptions.forbidden import ForbiddenException
from core.exceptions.invalid import InvalidException
from core.router.router import Router
from core.services.beneficiaries import BeneficiariesService
from core.services.groups import GroupsService
from core.services.logs import LogsService, Log, LogTag
from core.utils.consts import VALID_UNITS
from core.utils.key import split_key, split_line
from schema import SchemaError, Schema


class District(db.Model):
    __table_name__ = "districts"


class UsersCognito(CognitoService):
    __user_pool_id__ = os.environ.get("USER_POOL_ID", "TEST_POOL")


def create_group(event: HTTPEvent):
    district = event.params["district"]
    item = event.json
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

    if not event.authorizer.is_beneficiary:
        if event.authorizer.is_scouter:
            raise ForbiddenException('Scouters accounts can\'t be migrated to beneficiaries accounts yet')
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
        del response.item['beneficiary_code']
        del response.item['scouters_code']
    return JSONResponse(response.as_dict())


def get_group_stats(event: HTTPEvent):
    district_code = event.params["district"]
    code = event.params["group"]
    response = GroupsService.get(district_code, code, attributes=["scouters"])
    if response.item is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Group '{code}' was not found")
    unit: str = event.queryParams.get('unit')
    if unit is not None:
        unit = str(unit).lower()
        if unit not in VALID_UNITS:
            unit = None
    stats = {}
    beneficiaries = BeneficiariesService \
        .query_group(district_code, code, attributes=['user']) if unit is None else \
        BeneficiariesService.query_unit(district_code, code, unit, attributes=['user'])
    logs: List[Log] = []
    progress_logs: Dict[str, Dict[str, str]] = {}
    complete_logs: Dict[str, Dict[str, str]] = {}
    for beneficiary in beneficiaries:
        sub = beneficiary.user_sub
        beneficiary_logs = LogsService.query_stats_tags(user=sub)
        logs += beneficiary_logs
        progress_logs[sub] = [log for log in beneficiary_logs if log.parent_tag == LogTag.PROGRESS]
        complete_logs[sub] = [log for log in beneficiary_logs if log.parent_tag == LogTag.COMPLETED]

    stats['log_count'] = {
        tag.short: len([log for log in logs if log.parent_tag == tag]) for tag in LogTag
    }

    stats['completed_objectives'] = {sub: [{
        'stage': log.tags[1],
        'area': log.tags[2],
        'line': split_line(log.tags[3])[0],
        'subline': split_line(log.tags[3])[1],
        'timestamp': log.timestamp
    } for log in logs] for sub, logs in complete_logs.items()}

    stats['progress_logs'] = {sub: [{
        'stage': log.tags[1],
        'area': log.tags[2],
        'line': split_line(log.tags[3])[0],
        'subline': split_line(log.tags[3])[1],
        'timestamp': log.timestamp,
        'log': log.log if event.authorizer.sub not in response.item['scouters'].keys() else None
    } for log in logs] for sub, logs in progress_logs.items()}

    return JSONResponse(stats)


def join_group_as_scouter(event: HTTPEvent):
    district = event.params["district"]
    group = event.params["group"]
    code = event.json["code"]

    if not event.authorizer.is_scouter:
        if event.authorizer.is_beneficiary:
            raise ForbiddenException('Beneficiaries accounts can\'t be migrated to scouters accounts yet')
        UsersCognito.add_to_group(event.authorizer.username, "Scouters")
    GroupsService.join_as_scouter(event.authorizer, district, group, code)
    return JSONResponse({"message": "OK"})


router = Router()
router.get("/api/districts/{district}/groups/", list_groups)
router.get("/api/districts/{district}/groups/{group}/", get_group)
router.get("/api/districts/{district}/groups/{group}/stats/", get_group_stats)

router.post("/api/districts/{district}/groups/", create_group, schema=Schema({
    'code': str,
    'name': str
}))
router.post("/api/districts/{district}/groups/{group}/beneficiaries/join", join_group, schema=Schema({
    'code': str
}))
router.post("/api/districts/{district}/groups/{group}/scouters/join", join_group_as_scouter, schema=Schema({
    'code': str
}))


def handler(event, _) -> dict:
    event = HTTPEvent(event)
    result = router.route(event)
    return result.as_dict()
