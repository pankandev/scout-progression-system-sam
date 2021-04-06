from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.db.results import QueryResult
from core.exceptions.forbidden import ForbiddenException
from core.router.router import Router
from core.services.logs import LogsService
from core.utils import join_key


def query_logs(event: HTTPEvent):
    user_sub = event.params['sub']
    tag = event.params['tag']

    if not event.authorizer.is_scouter and event.authorizer.sub != user_sub:
        raise ForbiddenException("Only an scouter and the same user can get these logs")

    logs = LogsService.query(user_sub, tag)
    return JSONResponse(body=QueryResult.from_list([log.to_map() for log in logs]).as_dict())


def create_log(event: HTTPEvent):
    return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")


router = Router()

router.get("/api/users/{sub}/logs/{tag}/", query_logs)
router.post("/api/users/{sub}/logs/{tag}/", create_log)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
