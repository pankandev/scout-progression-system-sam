import os

from core import db, HTTPEvent
from core.aws.response import JSONResponse


class District(db.Model):
    __table_name__ = "district"


class Group(db.Model):
    __table_name__ = "group"


def add_url(item: dict, event: HTTPEvent):
    item["district-url"] = os.path.join(event.url, "districts", item["district"])
    item["url"] = os.path.join(event.url, "districts", item["district"], "groups", item["code"])


def handler(event, _):
    event = HTTPEvent(event)
    district_code = event.params["district"]
    code = event.params.get("group")

    if code is None:
        if District.get({"code": district_code}).item is None:
            return JSONResponse({
                "error": "NOT_FOUND",
                "message": f"District '{district_code}' was not found"
            }, status=404).as_dict()

        response = Group.query(key_conditions={
            "district": {
                "AttributeValueList": [district_code],
                "ComparisonOperator": "EQ"
            }
        }, limit=10)
        for item in response.items:
            add_url(item, event)
    else:
        response = Group.get({"district": district_code, "code": code})
        if response.item is None:
            return JSONResponse({
                "error": "NOT_FOUND",
                "message": f"Group '{code}' was not found"
            }, status=404).as_dict()
        add_url(response.item, event)
    return JSONResponse(response.as_dict()).as_dict()
