import os

from core import db, HTTPEvent, JSONResponse


class Tasks(db.Model):
    __table_name__ = "tasks"


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    code = event.params.get("district")

    return JSONResponse({"error": "NOT_IMPLEMENTED"}).as_dict()
