import json
from typing import List

from schema import Schema, SchemaError

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.exceptions.notfound import NotFoundException
from core.router.router import Router
from core.services.rewards import RewardsService, RewardSet, Reward, RewardType, RewardProbability, RewardRarity
from core.services.tasks import TasksService, ObjectiveKey
from core.utils.consts import VALID_STAGES, VALID_AREAS


# GET  /api/users/{sub}/tasks/
def list_user_tasks(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']
    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    return JSONResponse(TasksService.query(event.authorizer).as_dict())


# GET  /api/users/{sub}/tasks/{stage}/
def list_user_stage_tasks(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']
    stage = event.params['stage']
    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    return JSONResponse(TasksService.query(event.authorizer, stage).as_dict())


# GET  /api/users/{sub}/tasks/{stage}/{area}/
def list_user_area_tasks(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']
    stage = event.params['stage']
    area = event.params['area']
    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    return JSONResponse(TasksService.query(event.authorizer, stage, area).as_dict())


# GET  /api/users/{sub}/tasks/{stage}/{area}/{subline}/
def get_user_task(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']
    stage = event.params['stage']
    if stage not in VALID_STAGES:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Stage {stage} not found")
    area = event.params['area']
    if area not in VALID_AREAS:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Area {area} not found")
    subline = event.params['subline']
    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    result = TasksService.get(event.authorizer, stage, area, subline)
    if result.item is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, "Task not found")
    return JSONResponse(result.as_dict())


# GET  /api/users/{sub}/tasks/active/
def get_user_active_task(event: HTTPEvent) -> JSONResponse:
    sub = event.params['sub']
    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    result = TasksService.get_active_task(event.authorizer)
    if result is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, "No active tasks")
    return JSONResponse(result.as_dict())


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

    return JSONResponse(
        {
            'message': 'Completed task',
            'task': completed_task,
            'reward': RewardsService.generate_reward_token(
                authorizer=event.authorizer,
                static=RewardSet(rewards=[
                    RewardProbability(RewardType.NEEDS, RewardRarity.RARE),
                    RewardProbability(RewardType.ZONE, RewardRarity.RARE),
                    RewardProbability(RewardType.POINTS, RewardRarity.RARE),
                ]),
                boxes=[
                    RewardSet(
                        rewards=[
                            RewardProbability(RewardType.AVATAR, RewardRarity.RARE),
                            RewardProbability(RewardType.DECORATION, RewardRarity.COMMON),
                        ]
                    ),
                    RewardSet(
                        rewards=[
                            RewardProbability(RewardType.DECORATION, RewardRarity.RARE),
                            RewardProbability(RewardType.AVATAR, RewardRarity.COMMON),
                        ]
                    ),
                    RewardSet(
                        rewards=[
                            RewardProbability(RewardType.DECORATION, RewardRarity.RARE),
                            RewardProbability(RewardType.AVATAR, RewardRarity.RARE),
                        ]
                    ),
                ]
            ),
        }
    )


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

    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
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

router.get("/api/users/{sub}/tasks/", list_user_tasks)
router.get("/api/users/{sub}/tasks/{stage}/", list_user_tasks)
router.get("/api/users/{sub}/tasks/{stage}/{area}/", list_user_area_tasks)
router.get("/api/users/{sub}/tasks/{stage}/{area}/{subline}/", get_user_task)
router.get("/api/users/{sub}/tasks/active/", get_user_active_task)

router.post("/api/users/{sub}/tasks/{stage}/{area}/{subline}/", start_task)
router.post("/api/users/{sub}/tasks/active/complete/", complete_active_task)
router.post("/api/users/{sub}/tasks/initialize/", initialize_tasks)

router.put("/api/users/{sub}/tasks/active/", update_active_task)

router.delete("/api/users/{sub}/tasks/active/", dismiss_active_task)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
