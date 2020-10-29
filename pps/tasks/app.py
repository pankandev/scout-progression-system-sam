from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.services.tasks import TasksService


def get_handler(event: HTTPEvent):
    if event.resource.split('/')[-1] == 'tasks':
        sub = event.params['sub']
        if event.authorizer.sub != sub:
            return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
        return TasksService.query(event.authorizer)
    return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")


def post_handler(event: HTTPEvent):
    if event.resource.split('/')[-1] == 'tasks':
        sub = event.params['sub']
        if event.authorizer.sub != sub:
            return JSONResponse.generate_error(HTTPError.FORBIDDEN, "You have no access to this resource with this user")
        return TasksService.query(event.authorizer)
    return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    if event.method == "GET":
        response = get_handler(event)
    return response.as_dict()
