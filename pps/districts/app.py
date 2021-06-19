from typing import Dict

from core import db, HTTPEvent, JSONResponse
from core.exceptions.notfound import NotFoundException
from core.router.router import Router


class DistrictModel(db.Model):
    __table_name__ = "districts"


class District:
    code: str
    name: str

    def __init__(self, code: str, name: str):
        self.code = code
        self.name = name

    @staticmethod
    def from_db(data: Dict[str, str]):
        return District(data.get('code'), data.get('name'))

    def to_api_map(self) -> Dict[str, str]:
        return {
            'code': self.code,
            'name': self.name
        }


def get_district(event: HTTPEvent):
    code = event.params["district"]

    response = DistrictModel.get({"code": code})
    if response.item is None:
        raise NotFoundException(f"District '{code}' was not found")
    response.item = District.from_db(response.item).to_api_map()
    return JSONResponse(response.as_dict())


def get_all_districts(_: HTTPEvent):
    response = DistrictModel.scan()
    response.items = [District.from_db(item).to_api_map() for item in response.items]
    return JSONResponse(response.as_dict())


router = Router()
router.get('/api/districts/', get_all_districts)
router.get('/api/districts/{district}/', get_district)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    return router.route(event).as_dict()
