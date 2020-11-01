from schema import Schema, SchemaError

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.exceptions.notfound import NotFoundException
from core.services.tasks import TasksService
from core.utils.consts import VALID_STAGES, VALID_AREAS

"""
List user tasks:
GET  /api/users/{sub}/tasks/
List user stage tasks:
GET  /api/users/{sub}/tasks/{stage}/
List user area tasks:
GET  /api/users/{sub}/tasks/{stage}/{area}/
Get user task:
GET  /api/users/{sub}/tasks/{stage}/{area}/{subline}/
Get active task:
GET  /api/districts/{sub}/tasks/active/

Start task:
POST /api/users/{sub}/tasks/{stage}/{area}/{subline}/
Update active task:
PATCH /api/users/{sub}/tasks/active/
Dismiss active task:
DELETE /api/users/{sub}/tasks/active/
Complete active task:
POST /api/users/{sub}/tasks/active/complete/
"""


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
    return JSONResponse(TasksService.get_active_task(event.authorizer).as_dict())


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
    body = schema.validate(event.body)

    if event.authorizer.sub != sub:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    try:
        TasksService.start_task(event.authorizer, stage, area, subline, body['sub-tasks'],
                                body['description'])
    except NotFoundException:
        JSONResponse.generate_error(HTTPError.NOT_FOUND, 'Objective not found')
    return JSONResponse({'message': 'Created new task'})


# PATCH /api/users/{sub}/tasks/active/
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
        body = schema.validate(event.body)
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
    return JSONResponse(
        {
            'message': 'Completed task',
            'task': TasksService.complete_active_task(event.authorizer)
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


def get_handler(event: HTTPEvent):
    last_section = event.resource.split('/')[-1]
    if last_section == 'tasks':
        return list_user_tasks(event)
    if last_section == '{stage}':
        return list_user_stage_tasks(event)
    if last_section == '{area}':
        return list_user_area_tasks(event)
    if last_section == '{subline}':
        return get_user_task(event)
    if last_section == 'active':
        return get_user_active_task(event)
    return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")


def post_handler(event: HTTPEvent):
    last_section = event.resource.split('/')[-1]
    if last_section == '{subline}':
        return start_task(event)
    if last_section == 'complete':
        return complete_active_task(event)
    return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")


def put_handler(event: HTTPEvent):
    last_section = event.resource.split('/')[-1]
    if last_section == 'active':
        return update_active_task(event)
    return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")


def delete_handler(event: HTTPEvent):
    last_section = event.resource.split('/')[-1]
    if last_section == 'active':
        return dismiss_active_task(event)
    return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    if event.method == "GET":
        response = get_handler(event)
    elif event.method == "POST":
        response = post_handler(event)
    elif event.method == "PUT":
        response = put_handler(event)
    elif event.method == "DELETE":
        response = delete_handler(event)
    else:
        response = JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Bad method: {event.method}")
    return response.as_dict()
