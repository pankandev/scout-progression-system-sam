from schema import Schema, SchemaError

from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.exceptions.forbidden import ForbiddenException
from core.exceptions.invalid import InvalidException
from core.exceptions.notfound import NotFoundException
from core.router.router import Router
from core.services.beneficiaries import BeneficiariesService
from core.services.rewards import RewardsService, RewardType, RewardRarity, Reward
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


def get_my_rewards(event: HTTPEvent):
    category_name: str = event.params.get('category')
    category = RewardType.from_value(category_name.upper())
    return JSONResponse({
        'rewards': [log.to_map() for log in RewardsService.get_user_rewards(event.authorizer, category)]
    })


def create_item(event: HTTPEvent):
    category = event.params['category']

    try:
        release = int(event.params['release'])
    except ValueError:
        return JSONResponse.generate_error(HTTPError.INVALID_CONTENT,
                                           f"Invalid release {event.params['release']}, it should be an int")

    body = event.json
    body['category'] = category
    body['release'] = release

    reward = Reward.from_api_map(body)
    result = RewardsService.create(reward.description, reward.type, reward.release,
                                   reward.rarity, reward.price)
    reward = Reward.from_db_map(result.item)
    return JSONResponse({
        'message': 'Created item',
        'item': reward.to_api_map()
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
    box_index = body.get('box_index')
    if box_index is not None:
        try:
            box_index = int(box_index)
        except ValueError:
            raise InvalidException('Box index must be an int')
    rewards = RewardsService.claim_reward(event.authorizer, reward_token=token, box_index=box_index,
                                          release=1)
    return JSONResponse({'message': 'Claimed rewards!', 'rewards': [reward.to_api_map() for reward in rewards]})


router.get("/api/rewards/{category}/{release}/", list_shop_category)
router.get("/api/rewards/{category}/{release}/{id}/", get_item)
router.get("/api/rewards/mine/{category}", get_my_rewards)

router.post("/api/rewards/{category}/{release}/", create_item)
router.post("/api/rewards/{category}/{release}/{id}/buy/{area}/", buy_item)
router.post("/api/rewards/claim/", claim_reward)


def handler(event: dict, _) -> dict:
    event = HTTPEvent(event)
    response = router.route(event)
    return response.as_dict()
