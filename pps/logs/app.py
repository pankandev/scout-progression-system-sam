import json
import time

from schema import Schema, SchemaError, Optional

from core import HTTPEvent, JSONResponse
from core.db.results import QueryResult
from core.exceptions.forbidden import ForbiddenException
from core.exceptions.invalid import InvalidException
from core.router.router import Router
from core.services.logs import LogsService
from core.services.rewards import RewardsService, RewardSet, Reward, RewardType, RewardProbability, RewardRarity, \
    RewardsFactory, RewardReason
from core.services.tasks import TasksService
from core.utils.key import split_key, join_key

USER_VALID_TAGS = ['PROGRESS']


def query_logs(event: HTTPEvent):
    user_sub = event.params['sub']
    tag = event.params['tag']

    if not event.authorizer.is_scouter and event.authorizer.sub != user_sub:
        raise ForbiddenException("Only an scouter and the same user can get these logs")

    limit = event.queryParams.get('limit', 25)
    if not isinstance(limit, int) or limit > 100:
        raise InvalidException("Limit must be an integer and lower or equal than 100")

    logs = LogsService.query(user_sub, tag, limit=limit)
    return JSONResponse(body=QueryResult.from_list([log.to_map() for log in logs]).as_dict())


def create_log(event: HTTPEvent):
    user_sub = event.params['sub']
    tag = event.params['tag']

    if event.authorizer.sub != user_sub:
        raise ForbiddenException("Only the same user can create logs")
    parent_tag = split_key(tag)[0]
    if parent_tag not in USER_VALID_TAGS:
        raise ForbiddenException(f"A user can only create logs with the following tags: {USER_VALID_TAGS}")

    body = event.json
    try:
        Schema({
            'log': str,
            Optional('data'): dict,
            Optional('token'): str
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

    if parent_tag == 'PROGRESS':
        if parent_tag != tag:
            raise InvalidException(f"A progress log tag can't be compound")
        if body.get('token') is None:
            raise InvalidException(f"To post a PROGRESS log you must provide the task token")
        objective = TasksService.get_task_token_objective(body['token'], authorizer=event.authorizer)
        tag = join_key("PROGRESS", objective)

    log = LogsService.create(user_sub, tag, log_text=log, data=body.get('data'))
    response_body = {'item': log.to_map()}

    if parent_tag == 'PROGRESS':
        last_progress_log = LogsService.get_last_log_with_tag(event.authorizer.sub, tag)
        if last_progress_log is not None and int(
                time.time() * 1000
        ) - last_progress_log.timestamp > 24 * 60 * 60 * 1000:
            response_body['token'] = RewardsFactory.get_reward_token_by_reason(authorizer=event.authorizer,
                                                                               reason=RewardReason.PROGRESS_LOG)
    return JSONResponse(body=response_body)


router = Router()

router.get("/api/users/{sub}/logs/{tag}/", query_logs)
router.post("/api/users/{sub}/logs/{tag}/", create_log)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
