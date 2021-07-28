import time
from typing import List, Optional

from core.utils.key import split_key
from schema import Schema, SchemaError

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.exceptions.notfound import NotFoundException
from core.router.router import Router
from core.services.logs import LogsService, LogTag
from core.services.rewards import RewardsFactory, RewardReason
from core.services.tasks import TasksService, ObjectiveKey, Task
from core.utils import join_key
from core.utils.consts import VALID_STAGES, VALID_AREAS


# GET  query user tasks
def fetch_user_tasks(event: HTTPEvent) -> JSONResponse:
    sub = event.params.get('sub')
    stage = event.params.get('stage')
    area = event.params.get('area')
    if stage is not None and stage not in VALID_STAGES:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Stage {stage} not found")
    if area is not None and area not in VALID_AREAS:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Area {area} not found")
    line_key: Optional[str] = event.params.get('subline')
    if line_key is not None:
        lines = line_key.split('.')
        if len(lines) != 2:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Subline {line_key} not valid")
        line, subline = lines
        try:
            line = int(line)
            subline = int(subline)
        except ValueError:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Subline {line_key} not valid")
        result = TasksService.get(sub, stage, area, line, subline).to_api_dict()
    else:
        result = TasksService.query(sub, stage, area).as_dict(lambda t: t.to_api_dict())
    return JSONResponse(result)


# GET  /api/users/{sub}/tasks/active/
def get_user_active_task(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']
    result = TasksService.get_active_task(sub)
    beneficiary_authorizer = event.authorizer if event.authorizer is not None and event.authorizer.sub == sub else None
    d = result.to_api_dict(authorizer=beneficiary_authorizer)
    if beneficiary_authorizer is not None:
        # generate log reward claim token
        last_task_log = LogsService.get_last_log_with_tag(sub, tag=join_key(LogTag.PROGRESS.value,
                                                                            result.objective_key).upper())
        d['eligible_for_progress_reward'] = last_task_log is None or int(
            time.time() * 1000
        ) - last_task_log.timestamp > 24 * 60 * 60 * 1000

    return JSONResponse(d)


# POST /api/users/{sub}/tasks/{stage}/{area}/{subline}/
def start_task(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']
    stage = event.params['stage']
    area = event.params['area']
    subline = event.params['subline']

    schema = Schema({
        'description': str,
        'sub-tasks': [str]
    })

    try:
        body = schema.validate(event.json)
    except SchemaError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, str(e))

    if event.authorizer.sub != sub:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    try:
        task = TasksService.start_task(event.authorizer, stage, area, subline, body['sub-tasks'], body['description'])
        if task is None:
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, 'An active task already exists')
    except NotFoundException:
        JSONResponse.generate_error(HTTPError.NOT_FOUND, 'Objective not found')
    return JSONResponse({'message': 'Started new task'})


# PUT /api/users/{sub}/tasks/active/
def update_active_task(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']

    schema = Schema({
        'description': str,
        'sub-tasks': [{
            'description': str,
            'completed': bool
        }]
    })

    try:
        body = schema.validate(event.json)
    except SchemaError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, str(e))

    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    return JSONResponse(
        {
            'message': 'Updated active task',
            'active-task': TasksService.update_active_task(event.authorizer, body['description'], body['sub-tasks'])
        }
    )


# POST /api/users/{sub}/tasks/active/complete/
def complete_active_task(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']

    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    completed_task = TasksService.complete_active_task(event.authorizer)
    if completed_task is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, "No active task found")

    area = split_key(completed_task['objective'])[1]

    response = JSONResponse(
        {
            'message': 'Completed task',
            'task': completed_task,
            'reward': RewardsFactory.get_reward_token_by_reason(
                authorizer=event.authorizer,
                area=area,
                reason=RewardReason.COMPLETE_OBJECTIVE
            ),
        }
    )
    LogsService.create(event.authorizer.sub, LogTag.COMPLETED.join(completed_task['objective'].upper()),
                       'Completed an objective!', {})
    return response


# DELETE /api/users/{sub}/tasks/active/complete/
def dismiss_active_task(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']

    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    return JSONResponse(
        {
            'message': 'Task dismissed',
            'task': TasksService.dismiss_active_task(event.authorizer)
        }
    )


# POST /api/users/{sub}/tasks/base/initialize/
def initialize_tasks(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']

    if event.authorizer.sub != sub:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")

    body = event.json
    if 'objectives' not in body:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, "No objectives found")
    if not isinstance(body['objectives'], list):
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, "Objectives must be a list of objects")

    objectives: List[ObjectiveKey] = []
    for obj in body['objectives']:
        if not isinstance(obj, dict):
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, "Each objective must be an object")
        if 'line' not in obj or not isinstance(obj['line'], int):
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT,
                                               "Each objective must have the key 'line' and it must be an int")
        if 'subline' not in obj or not isinstance(obj['subline'], int):
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT,
                                               "Each objective must have the key 'subline' and it must be an int")
        if 'area' not in obj or obj['area'] not in VALID_AREAS:
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT,
                                               f"Each objective must have the key 'area' and it must a valid area "
                                               f"name: {VALID_AREAS}")
        objectives.append(ObjectiveKey(line=obj['line'], subline=obj['subline'], area=obj['area']))

    return JSONResponse(
        {
            'message': 'Task dismissed',
            'reward': TasksService.initialize(event.authorizer, objectives)
        }
    )


router = Router()

router.get("/api/users/{sub}/tasks/", fetch_user_tasks, authorized=False)
router.get("/api/users/{sub}/tasks/{stage}/", fetch_user_tasks, authorized=False)
router.get("/api/users/{sub}/tasks/{stage}/{area}/", fetch_user_tasks, authorized=False)
router.get("/api/users/{sub}/tasks/{stage}/{area}/{subline}/", fetch_user_tasks, authorized=False)
router.get("/api/users/{sub}/tasks/active/", get_user_active_task, authorized=False)

router.post("/api/users/{sub}/tasks/{stage}/{area}/{subline}/", start_task)
router.post("/api/users/{sub}/tasks/active/complete/", complete_active_task)
router.post("/api/users/{sub}/tasks/initialize/", initialize_tasks)

router.put("/api/users/{sub}/tasks/active/", update_active_task)

router.delete("/api/users/{sub}/tasks/active/", dismiss_active_task)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
