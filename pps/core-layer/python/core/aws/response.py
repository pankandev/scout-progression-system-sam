import json
from decimal import Decimal

from .errors import HTTPError, ERROR_CODES


class JSONResponse:
    def __init__(self, body: dict, status: int = 200):
        self.body = body
        self.status = status

    @staticmethod
    def clean_for_json(item):
        if type(item) is dict:
            for key, value in item.items():
                item[key] = JSONResponse.clean_for_json(value)
        elif type(item) is Decimal:
            if float(item) == int(item):
                return int(item)
            else:
                return float(item)
        return item

    def as_dict(self):
        return {
            "statusCode": self.status,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Credentials": True
            },
            "body": json.dumps(JSONResponse.clean_for_json(self.body))
        }

    @staticmethod
    def generate_error(code: HTTPError, message: str):
        return JSONResponse({
            "error": str(code),
            "message": message
        }, ERROR_CODES.get(code, 200))
