from core import HTTPEvent, JSONResponse


def handler(event: dict, _) -> dict:
    return JSONResponse({"error": "NOT_IMPLEMENTED"}).as_dict()
