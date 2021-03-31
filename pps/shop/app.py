from schema import Schema, SchemaError

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.exceptions.forbidden import ForbiddenException
from core.exceptions.invalid import InvalidException
from core.exceptions.notfound import NotFoundException
from core.router.router import Router
from core.services.beneficiaries import BeneficiariesService
from core.services.rewards import RewardsService, RewardType, RewardRarity
from core.utils.consts import VALID_AREAS

router = Router()


def list_shop_category(event: HTTPEvent):
    category = event.params['category']

    try:
        release = int(event.params['release'])
    except ValueError:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT,
                                           f"Invalid release {event.params['release']}, it should be an int")

    return JSONResponse(RewardsService.query(RewardType.from_value(category.upper()), release).as_dict())


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

    return JSONResponse(RewardsService.get(category, release, id_).as_dict())


def get_my_items(event: HTTPEvent):
    return JSONResponse(BeneficiariesService.get(event.authorizer.sub, ['bought_items']).as_dict())


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
        'description': str,
        'price': int,
        'rarity': str
    })
    try:
        body = schema.validate(body)
    except SchemaError as e:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, str(e))

    result = RewardsService.create(body['description'], RewardType.from_value(category.upper()), release,
                                   RewardRarity.from_name(body['rarity']), body['price']).as_dict()
    return JSONResponse({
        'message': 'Created item',
        'item': result
    })


def buy_item(event: HTTPEvent):
    category = event.params['category']

    try:
        release = int(event.params['release'])
    except ValueError:
        return NotFoundException(f"Unknown release {event.params['release']}, it should be an int")

    try:
        id_ = int(event.params['id'])
    except ValueError:
        raise NotFoundException(f"Unknown id {event.params['id']}, it should be an int")

    area = event.params['area']
    if area not in VALID_AREAS:
        raise NotFoundException(f"Area {area} does not exist")

    amount = event.json.get('amount', 1)
    if type(amount) is not int:
        raise InvalidException(f"The amount to be bought must be an integer")
    if amount < 1:
        raise InvalidException(f"The amount must be one or more")

    try:
        result = BeneficiariesService.buy_item(event.authorizer, area, category, release, id_, amount)
    except BeneficiariesService.exceptions().ConditionalCheckFailedException:
        raise ForbiddenException(f"You don't have enough {area} score to buy this item")

    if not result:
        return NotFoundException(f"Item not found")
    return JSONResponse(result)


def claim_reward(event: HTTPEvent):
    body = event.json
    token = body.get('token')
    if token is None:
        raise InvalidException('No reward token given')
    rewards = RewardsService.claim_reward(event.authorizer, token, box_index=body.get('box_index'))
    return JSONResponse({'message': 'Claimed rewards!', 'rewards': [reward.to_map() for reward in rewards]})


router.get("/api/rewards/{category}/{release}/", list_shop_category)
router.get("/api/rewards/{category}/{release}/{id}/", get_item)
router.get("/api/rewards/my-items/", get_my_items)

router.post("/api/rewards/{category}/{release}/", create_item)
router.post("/api/rewards/{category}/{release}/{id}/buy/{area}/", buy_item)
router.post("/api/rewards/claim/", claim_reward)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
