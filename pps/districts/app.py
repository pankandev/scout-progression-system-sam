from core import db, HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.router.router import Router


class District(db.Model):
    __table_name__ = "districts"


def add_url(item: dict, event: HTTPEvent):
    item["url"] = event.concat_url("districts", item["code"])


def get_district(event: HTTPEvent):
    code = event.params["district"]

    response = District.get({"code": code})
    if response.item is None:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"District '{code}' was not found")
    add_url(response.item, event)
    return JSONResponse(response.as_dict())


def get_all_districts(event: HTTPEvent):
    response = District.scan()
    for item in response.items:
        add_url(item, event)
    return JSONResponse(response.as_dict())


router = Router()
router.get('/api/districts/', get_all_districts)
router.get('/api/districts/{district}/', get_district)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    return router.route(event).as_dict()
