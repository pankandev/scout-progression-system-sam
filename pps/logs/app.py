import json

from schema import Schema, SchemaError, Optional

from core import HTTPEvent, JSONResponse
from core.db.results import QueryResult
from core.exceptions.forbidden import ForbiddenException
from core.exceptions.invalid import InvalidException
from core.router.router import Router
from core.services.logs import LogsService
from core.utils.key import split_key

USER_VALID_TAGS = ['PROGRESS']

def query_logs(event: HTTPEvent):
    user_sub = event.params['sub']
    tag = event.params['tag']

    if not event.authorizer.is_scouter and event.authorizer.sub != user_sub:
        raise ForbiddenException("Only an scouter and the same user can get these logs")

    logs = LogsService.query(user_sub, tag)
    return JSONResponse(body=QueryResult.from_list([log.to_map() for log in logs]).as_dict())


def create_log(event: HTTPEvent):
    user_sub = event.params['sub']
    tag = event.params['tag']

    if event.authorizer.sub != user_sub:
        raise ForbiddenException("Only the same user can create logs")
    if split_key(tag)[0] not in USER_VALID_TAGS:
        raise ForbiddenException(f"A user can only create logs with the following tags: {USER_VALID_TAGS}")

    body = event.json
    try:
        Schema({
            'log': str,
            Optional('data'): dict
        }).validate(body)
    except SchemaError as e:
        raise InvalidException(f'Request body is invalid: {e.errors}')

    log = body['log']
    data = body.get('data')

    if len(body) > 1024:
        raise InvalidException(f"A log can't have more than 1024 characters")

    if data is not None:
        if len(json.dumps(data)) > 2048:
            raise InvalidException(f"Log data is too big")

    log = LogsService.create(user_sub, tag, log_text=log, data=body.get('data'))
    return JSONResponse(body={'item': log.to_map()})


router = Router()

router.get("/api/users/{sub}/logs/{tag}/", query_logs)
router.post("/api/users/{sub}/logs/{tag}/", create_log)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
