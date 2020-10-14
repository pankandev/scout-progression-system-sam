import os

from core import db, HTTPEvent
from core.aws.errors import HTTPError
from core.aws.response import JSONResponse


class District(db.Model):
    __table_name__ = "districts"


class Group(db.Model):
    __table_name__ = "groups"


def process_group(item: dict, event: HTTPEvent):
    item["district-url"] = event.concat_url("districts", item["district"])
    item["url"] = event.concat_url("districts", item["district"], "groups", item["code"])


def get_handler(event: HTTPEvent):
    district_code = event.params["district"]
    code = event.params.get("group")

    if code is None:
        # get all groups from district
        if District.get({"code": district_code}).item is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"District '{district_code}' was not found")

        response = Group.query(keys={"district": district_code}, limit=10)
        for item in response.items:
            process_group(item, event)
    else:
        # get one group
        response = Group.get({"district": district_code, "code": code})
        if response.item is None:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Group '{code}' was not found")
        process_group(response.item, event)
    return JSONResponse(response.as_dict())


def handler(event, _) -> dict:
    event = HTTPEvent(event)
    return get_handler(event).as_dict()
