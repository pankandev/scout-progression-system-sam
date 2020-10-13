import os

from core import db, HTTPEvent, JSONResponse


class Objectives(db.Model):
    __table_name__ = "objectives"


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    code = event.params.get("district")

    return JSONResponse({"error": "NOT_IMPLEMENTED"}).as_dict()
