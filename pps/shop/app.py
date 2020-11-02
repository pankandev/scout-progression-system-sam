from schema import Schema, SchemaError

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.router.router import Router
from core.services.beneficiaries import BeneficiariesService
from core.services.shop import ShopService
from core.utils.consts import VALID_AREAS

router = Router()


def list_shop_category(event: HTTPEvent):
    category = event.params['category']

    try:
        release = int(event.params['release'])
    except ValueError:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT,
                                           f"Invalid release {event.params['release']}, it should be an int")

    return JSONResponse(ShopService.query(category, release).as_dict())


def get_item(event: HTTPEvent):
    category = event.params['category']

    try:
        release = int(event.params['release'])
    except ValueError:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND,
                                           f"Unknown release {event.params['release']}, it should be an int")

    try:
        id_ = int(event.params['id'])
    except ValueError:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND,
                                           f"Unknown id {event.params['id']}, it should be an int")

    return JSONResponse(ShopService.get(category, release, id_).as_dict())


def create_item(event: HTTPEvent):
    category = event.params['category']

    try:
        release = int(event.params['release'])
    except ValueError:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT,
                                           f"Invalid release {event.params['release']}, it should be an int")

    body = event.json

    try:
        body['price'] = int(body.get('price'))
    except ValueError:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT,
                                           f"Invalid price {body['price']}, it should be an int")

    schema = Schema({
        'name': str,
        'description': str,
        'price': int
    })
    try:
        schema.validate(body)
    except SchemaError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, str(e))

    result = ShopService.create(body['name'], body['description'], body['price'], category, release).as_dict()
    return JSONResponse({
        'message': 'Created item',
        'item': result
    })


def buy_item(event: HTTPEvent):
    category = event.params['category']

    try:
        release = int(event.params['release'])
    except ValueError:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND,
                                           f"Unknown release {event.params['release']}, it should be an int")

    try:
        id_ = int(event.params['id'])
    except ValueError:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND,
                                           f"Unknown id {event.params['id']}, it should be an int")

    area = event.params['area']
    if area not in VALID_AREAS:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Area {area} does not exist")

    amount = event.json.get('amount', 1)
    if type(amount) is not int:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, f"The amount to be bought must be an integer")
    if amount < 1:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, f"The amount must be one or more")

    try:
        result = BeneficiariesService.buy_item(event.authorizer, area, category, release, id_, amount)
    except BeneficiariesService.exceptions().ConditionalCheckFailedException:
        return JSONResponse.generate_error(HTTPError.FORBIDDEN, f"You don't have enough {area} score to buy this item")

    if not result:
        return JSONResponse.generate_error(HTTPError.NOT_FOUND, f"Item not found")
    return JSONResponse(result)


router.get("/api/shop/{category}/{release}/", list_shop_category)
router.get("/api/shop/{category}/{release}/{id}/", get_item)

router.post("/api/shop/{category}/{release}/", create_item)
router.post("/api/shop/{category}/{release}/{id}/buy/{area}/", buy_item)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
