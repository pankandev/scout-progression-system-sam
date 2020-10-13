import json


class JSONResponse:
    def __init__(self, body: dict, status: int = 200):
        self.body = body
        self.status = status

    def as_dict(self):
        return {
            "statusCode": self.status,
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps(self.body)
        }
