from schema import Schema, SchemaError

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.services.tasks import TasksService

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
POST /api/users/{sub}/tasks/active/
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
    area = event.params['area']
    subline = event.params['subline']
    if event.authorizer.sub != sub and not event.authorizer.is_scouter:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
    return JSONResponse(TasksService.get(event.authorizer, stage, area, subline).as_dict())


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
    TasksService.start_task(event.authorizer, stage, area, subline, body['sub-tasks'],
                            body['description'])
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


def get_handler(event: HTTPEvent):
    if event.resource.split('/')[-1] == 'tasks':
        return list_user_tasks(event)
    return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")


def post_handler(event: HTTPEvent):
    if event.resource.split('/')[-1] == 'tasks':
        # create new task
        sub = event.params['sub']
        if event.authorizer.sub != sub:
            return JSONResponse.generate_error(HTTPError.FORBIDDEN,
                                               "You have no access to this resource with this user")
        tasks = TasksService.query(event.authorizer)

    return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    if event.method == "GET":
        response = get_handler(event)
    return response.as_dict()
