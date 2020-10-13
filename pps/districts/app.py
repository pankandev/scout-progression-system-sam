import os

from core import db, HTTPEvent, JSONResponse


class District(db.Model):
    __table_name__ = "district"


def add_url(item: dict, event: HTTPEvent):
    item["url"] = os.path.join(event.url, "districts", item["code"])


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    code = event.params.get("district")

    if code is None:
        response = District.scan(limit=10)
        for item in response.items:
            add_url(item, event)
    else:
        response = District.get({"code": code})
        if response.item is None:
            return JSONResponse({
                "error": "NOT_FOUND",
                "message": f"District '{code}' was not found"
            }, status=404).as_dict()
        add_url(response.item, event)
    return JSONResponse(response.as_dict()).as_dict()
