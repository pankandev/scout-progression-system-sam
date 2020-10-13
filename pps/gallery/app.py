from core import db, HTTPEvent, JSONResponse


class Beneficiaries(db.Model):
    __table_name__ = "beneficiaries"


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    code = event.params.get("district")

    return JSONResponse({"error": "NOT_IMPLEMENTED"}).as_dict()
