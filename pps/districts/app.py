from core import db, HTTPEvent, JSONResponse
from core.aws.errors import HTTPError


class District(db.Model):
    __table_name__ = "districts"


def add_url(item: dict, event: HTTPEvent):
    item["url"] = event.concat_url("districts", item["code"])


def get_handler(event: HTTPEvent) -> JSONResponse:
    code = event.params.get("district")

    if code is None:
        # get all districts
        response = District.scan()
        for item in response.items:
            add_url(item, event)
    else:
        # get one district
        response = District.get({"code": code})
        if response.item is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"District '{code}' was not found")
        add_url(response.item, event)
    return JSONResponse(response.as_dict())


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    return get_handler(event).as_dict()
