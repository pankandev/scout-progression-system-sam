import json
from datetime import datetime, timezone

from core import HTTPEvent, JSONResponse
from core.db.results import QueryResult
from core.exceptions.forbidden import ForbiddenException
from core.exceptions.invalid import InvalidException
from core.router.router import Router
from core.services.logs import LogsService, LogTag
from core.services.rewards import RewardsFactory, RewardReason
from core.services.tasks import TasksService
from core.utils.key import split_key, join_key
from schema import Schema, Optional

USER_VALID_TAGS = [LogTag.PROGRESS]


def query_logs(event: HTTPEvent):
    user_sub = event.params['sub']
    tag = LogTag.normalize(split_key(event.params['tag'])).upper() if event.params.get('tag') else None

    limit = event.queryParams.get('limit', 25)
    if not isinstance(limit, int) or limit > 100:
        raise InvalidException("Limit must be an integer and lower or equal than 100")

    logs = LogsService.query(user_sub, tag, limit=limit)
    return JSONResponse(body=QueryResult.from_list([log.to_api_map() for log in logs]).as_dict())


def create_log(event: HTTPEvent):
    user_sub: str = event.params['sub']
    tag: str = event.params['tag'].upper()

    if event.authorizer.sub != user_sub:
        raise ForbiddenException("Only the same user can create logs")
    parent_tag = LogTag.from_short(split_key(tag)[0])
    if parent_tag not in USER_VALID_TAGS:
        raise ForbiddenException(f"A user can only create logs with the following tags: {USER_VALID_TAGS}")

    body = event.json

    log = body['log']
    data = body.get('data')

    if len(body) > 1024:
        raise InvalidException(f"A log can't have more than 1024 characters")

    if data is not None:
        if len(json.dumps(data)) > 2048:
            raise InvalidException(f"Log data is too big")

    response_body = {}

    if parent_tag == LogTag.PROGRESS:
        if tag != parent_tag.short:
            raise InvalidException(f"A progress log tag can't be compound")
        if body.get('token') is None:
            raise InvalidException(f"To post a PROGRESS log you must provide the task token")

        objective = TasksService.get_task_token_objective(body['token'], authorizer=event.authorizer)
        tag = join_key(LogTag.PROGRESS.value, objective).upper()

        now = int(datetime.now(timezone.utc).timestamp() * 1000)
        last_progress_log = LogsService.get_last_log_with_tag(event.authorizer.sub, tag.upper())

        if last_progress_log is None or now - last_progress_log.timestamp > 24 * 60 * 60 * 1000:
            response_body['token'] = RewardsFactory.get_reward_token_by_reason(authorizer=event.authorizer,
                                                                               area=split_key(objective)[1],
                                                                               reason=RewardReason.PROGRESS_LOG)

    log = LogsService.create(user_sub, tag, log_text=log, data=body.get('data'), append_timestamp_to_tag=True)
    response_body['item'] = log.to_api_map()

    return JSONResponse(body=response_body)


router = Router()

router.get("/api/users/{sub}/logs/", query_logs, authorized=False)
router.get("/api/users/{sub}/logs/{tag}/", query_logs, authorized=False)
router.post("/api/users/{sub}/logs/{tag}/", create_log, schema=Schema({
    'log': str,
    Optional('data'): dict,
    Optional('token'): str
}))


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
