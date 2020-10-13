import os

from core import db, HTTPEvent, JSONResponse


class Scouter(db.Model):
    __table_name__ = "scouters"


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    code = event.params.get("district")

    return JSONResponse({"error": "NOT_IMPLEMENTED"}).as_dict()
