import json
import math
import os
import random
import time
from datetime import timedelta, timezone, datetime
from enum import Enum
from typing import List, Dict, Any, Optional

import jwt
from core import ModelService
from core.aws.event import Authorizer
from core.db.model import Operator
from core.exceptions.forbidden import ForbiddenException
from core.exceptions.invalid import InvalidException
from core.exceptions.notfound import NotFoundException
from core.services.logs import LogsService, Log, LogTag
from core.utils import join_key
from core.utils.config import config
from core.utils.consts import VALID_AREAS
from jwt.exceptions import JWTDecodeError
from jwt.utils import get_int_from_datetime

REWARDS_PER_RELEASE = 100000


class RewardRarity(Enum):
    COMMON = 1
    RARE = 2

    @staticmethod
    def from_name(name: str):
        for member in RewardRarity:
            if name.upper() == member.name:
                return member
        raise InvalidException(f"Unknown reward rarity: {name}")


class RewardType(Enum):
    POINTS = 'POINTS'
    DECORATION = 'DECORATION'
    AVATAR = 'AVATAR'
    NEEDS = 'NEEDS'
    ZONE = 'ZONE'

    @staticmethod
    def from_value(value: str):
        for member in RewardType:
            if value.upper() == member.value:
                return member
        raise InvalidException(f"Unknown reward type: {value}")


class Reward:
    type: RewardType
    description: Dict[str, Any]
    rarity: RewardRarity
    release: int
    id: int
    price: int

    def __init__(self, category: RewardType, release: int, id_: int, description: Dict[str, Any], rarity: RewardRarity,
                 price: int = None):
        self.type = category
        self.description = description
        self.release = release
        self.id = id_
        self.rarity = rarity
        self.price = price

    def to_api_map(self) -> dict:
        m = {
            "category": self.type.value,
            "release": int(self.release) if self.release is not None else None,
            "rarity": self.rarity.name,
            "description": self.description,
        }
        if self.id is not None:
            m["id"] = int(self.id)
        if self.price is not None:
            m["price"] = int(self.price)
        return m

    @classmethod
    def from_api_map(cls, item: dict):
        try:
            return Reward(
                category=RewardType.from_value(item['category']),
                release=int(item['release']),
                id_=item.get('id'),
                description=item['description'],
                rarity=RewardRarity.from_name(item['rarity']),
                price=item.get('price')
            )
        except KeyError as e:
            raise InvalidException(f'Missing key: {e.args}')

    @staticmethod
    def factory(category: RewardType, rarity: RewardRarity):
        if category == RewardType.POINTS:
            return Reward(
                category=RewardType.POINTS,
                release=0,
                rarity=rarity,
                id_=None,
                description={
                    'amount': config.rare_score if rarity == RewardRarity.RARE else config.normal_score
                }
            )
        elif category == RewardType.NEEDS:
            return Reward(
                category=RewardType.NEEDS,
                release=0,
                rarity=rarity,
                id_=None,
                description={
                    'hunger': 100,
                    'thirst': 100,
                }
            )

    @staticmethod
    def from_db_map(item: dict):
        release_id = int(abs(item['release-id']))
        release = int(release_id // REWARDS_PER_RELEASE) + 1
        id_ = int(release_id)
        item['release'] = release
        item['id'] = id_
        price = item.get('price')
        return Reward(category=RewardType.from_value(item["category"]), release=release, id_=id_,
                      description=item["description"], price=int(price) if price is not None else None,
                      rarity=RewardRarity.RARE if int(item['release-id']) < 0 else RewardRarity.COMMON)

    def __repr__(self):
        return f"Reward(type={self.type.value}, description={self.description})"


class RewardProbability:
    type: RewardType
    rarity: RewardRarity

    def __init__(self, category: RewardType, rarity: RewardRarity):
        self.type = category
        self.rarity = rarity

    def to_map(self) -> dict:
        return {
            "type": self.type.value,
            "rarity": self.rarity.name
        }

    @classmethod
    def from_map(cls, reward_map: Dict[str, Any]):
        return RewardProbability(
            category=RewardType.from_value(reward_map["type"]),
            rarity=RewardRarity.from_name(reward_map["rarity"])
        )


class RewardSet:
    rewards: List[RewardProbability]

    def __init__(self, rewards: List[RewardProbability]):
        self.rewards = rewards.copy()

    def to_map_list(self) -> List[dict]:
        return list(map(lambda r: r.to_map(), self.rewards))

    @staticmethod
    def from_map_list(rewards_map: List[dict]):
        return RewardSet(rewards=[RewardProbability.from_map(reward) for reward in rewards_map])


class RewardsService(ModelService):
    __table_name__ = "rewards"
    __partition_key__ = "category"
    __sort_key__ = "release-id"

    @classmethod
    def create(cls, description: Any, category: RewardType, release: int, rarity: RewardRarity, price: int = None):
        index = cls.get_interface()

        ms_time = int(time.time() * 1000)
        id_ = ms_time % REWARDS_PER_RELEASE
        release_id = abs(int((release - 1) * REWARDS_PER_RELEASE + id_))
        if rarity == RewardRarity.RARE:
            release_id = -release_id

        item = {
            'description': description,
            'rarity': rarity.name
        }
        if price is not None:
            item['price'] = price
        return index.create(category.name, item, release_id, raise_if_exists_sort=True, raise_if_exists_partition=True)

    @classmethod
    def query(cls, category: RewardType, release: int):
        index = cls.get_interface()
        result = index.query(category.name, (Operator.LESS_THAN, int((release + 1) * REWARDS_PER_RELEASE)),
                             attributes=['category', 'description', 'release-id', 'price', 'rarity'])
        for item in result.items:
            release = int(item['release-id'] // REWARDS_PER_RELEASE)
            id_ = int(item['release-id'] % REWARDS_PER_RELEASE)
            item['release'] = release
            item['id'] = id_
            del item['release-id']
        return result

    @classmethod
    def get_random(cls, category: RewardType, release: int, rarity: RewardRarity):
        reward = Reward.factory(category, rarity)
        if reward is not None:
            return reward
        release = int(release)
        if release < 1:
            raise InvalidException('Release must be positive and non-zero')

        top = abs(release * REWARDS_PER_RELEASE - 1)
        if rarity == RewardRarity.RARE:
            top = -top

        lowest = min(0, top)
        highest = max(0, top)
        random_point = random.randint(lowest, highest)

        index = cls.get_interface()
        result = index.query(category.name,
                             (Operator.BETWEEN, lowest, random_point),
                             attributes=['category', 'description', 'release-id', 'price'], limit=1)
        if len(result.items) == 0:
            result = index.query(category.name,
                                 (Operator.BETWEEN, random_point, highest),
                                 attributes=['category', 'description', 'release-id', 'price'], limit=1)
        if len(result.items) == 0:
            raise NotFoundException(f'No reward of type {category.name} found')
        return Reward.from_db_map(result.items[0])

    @classmethod
    def get(cls, category: str, release: int, id_: int):
        index = cls.get_interface()
        release_id = release * REWARDS_PER_RELEASE + id_
        result = index.get(category, release_id, attributes=['name', 'category', 'description', 'release-id', 'price'])
        if result.item is None:
            return result

        release = result.item['release-id'] // REWARDS_PER_RELEASE
        id_ = result.item['release-id']
        result.item['release'] = release
        result.item['id'] = id_
        return result

    @classmethod
    def generate_reward_token(cls, authorizer: Authorizer, static: RewardSet = None, area: Optional[str] = None,
                              boxes: List[RewardSet] = None, duration: timedelta = None,
                              reason: Enum = None) -> str:
        from core.services.beneficiaries import BeneficiariesService

        if duration is None:
            duration = timedelta(days=7)
        jwk_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'jwk.json')

        with open(jwk_path, 'r') as f:
            jwk = jwt.jwk_from_dict(json.load(f))
        encoder = jwt.JWT()

        now = datetime.now(timezone.utc)
        token_index = int(BeneficiariesService.add_token_index(authorizer))
        payload = {
            "sub": authorizer.sub,
            "iat": get_int_from_datetime(now),
            "exp": get_int_from_datetime(now + duration),
            "static": static.to_map_list() if static is not None else [],
            "boxes": [box.to_map_list() for box in boxes] if boxes is not None else [],
            "index": token_index,
            "area": area,
            "reason": None if reason is None else reason.value
        }

        return encoder.encode(payload, jwk)

    @classmethod
    def claim_reward(cls, authorizer: Authorizer, reward_token: str, release: int, box_index: int = None) -> \
            List[Reward]:
        from core.services.beneficiaries import BeneficiariesService

        jwk_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'jwk.json')
        with open(jwk_path, 'r') as f:
            jwk = jwt.jwk_from_dict(json.load(f))

        decoder = jwt.JWT()
        try:
            decoded = decoder.decode(reward_token, jwk)
        except JWTDecodeError as e:
            raise InvalidException(f'Invalid token: {e.args}')

        now = get_int_from_datetime(datetime.now())
        if now > decoded["exp"]:
            raise ForbiddenException("The reward token has expired")
        if authorizer.sub != decoded["sub"]:
            raise ForbiddenException("This token does not belong to the claimer")
        BeneficiariesService.set_reward_index(authorizer, decoded['index'])

        boxes = decoded["boxes"]
        probabilities: List[RewardProbability] = [RewardProbability.from_map(reward) for reward in decoded["static"]]
        if len(boxes) > 0:
            if box_index is None:
                raise InvalidException("A box must be chosen")
            if box_index >= len(boxes):
                raise InvalidException(
                    f"Box index out of range, it must be between 0 (inclusive) and {len(boxes)} (exclusive)")
            probabilities += [RewardProbability.from_map(reward) for reward in boxes[box_index]]
        rewards = [RewardsService.get_random(probability.type, release, probability.rarity)
                   for probability in probabilities]
        LogsService.batch_create(logs=[
            Log(
                sub=authorizer.sub,
                tag=join_key(LogTag.REWARD.name, rewards[reward_i].type.name, rewards[reward_i].id),
                log='Won a reward',
                data=rewards[reward_i].to_api_map(),
                append_timestamp=rewards[reward_i].type != RewardType.AVATAR
            )
            for reward_i in range(len(rewards))])

        area: Optional[str] = decoded.get('area')
        areas: List[str] = VALID_AREAS if area is None else [area]

        scores = {}
        for r in rewards:
            if r.type != RewardType.POINTS:
                continue
            total_score = r.description['amount']
            for a in areas:
                scores[a] = scores.get(a, 0) + (total_score / len(areas))

        for key in scores:
            scores[key] = math.ceil(scores[key])

        BeneficiariesService.add_score(authorizer.sub, scores)
        return rewards

    @classmethod
    def get_user_rewards(cls, authorizer: Authorizer, category: RewardType):
        tag = join_key(LogTag.REWARD.name, category.name)
        return LogsService.query(authorizer.sub, tag, limit=None)


class RewardReason(Enum):
    PROGRESS_LOG = 'PROGRESS_LOG'
    COMPLETE_OBJECTIVE = 'COMPLETE_OBJECTIVE'
    INITIALIZE = 'INITIALIZE'


REWARDS_BY_REASON = {
    RewardReason.INITIALIZE: {
        'static': RewardSet(rewards=[
            RewardProbability(category=RewardType.POINTS,
                              rarity=RewardRarity.RARE),
            RewardProbability(category=RewardType.NEEDS,
                              rarity=RewardRarity.RARE),
        ]),
        'boxes': [
            RewardSet(rewards=[
                RewardProbability(
                    category=RewardType.ZONE,
                    rarity=RewardRarity.RARE
                )
            ]),
            RewardSet(rewards=[
                RewardProbability(
                    category=RewardType.DECORATION,
                    rarity=RewardRarity.RARE
                )
            ]),
            RewardSet(rewards=[
                RewardProbability(
                    category=RewardType.AVATAR,
                    rarity=RewardRarity.RARE
                )
            ]),
        ]
    },
    RewardReason.PROGRESS_LOG: {
        'static': RewardSet(
            rewards=[
                RewardProbability(
                    category=RewardType.NEEDS,
                    rarity=RewardRarity.COMMON
                ),
                RewardProbability(
                    category=RewardType.POINTS,
                    rarity=RewardRarity.COMMON
                )
            ]
        ),
        'boxes': [
            RewardSet(
                rewards=[
                    RewardProbability(
                        category=RewardType.AVATAR,
                        rarity=RewardRarity.COMMON
                    )
                ]
            ),
            RewardSet(
                rewards=[
                    RewardProbability(
                        category=RewardType.AVATAR,
                        rarity=RewardRarity.COMMON
                    )
                ]
            ),
            RewardSet(
                rewards=[
                    RewardProbability(
                        category=RewardType.AVATAR,
                        rarity=RewardRarity.RARE
                    )
                ]
            ),
            RewardSet(
                rewards=[
                    RewardProbability(
                        category=RewardType.DECORATION,
                        rarity=RewardRarity.COMMON
                    )
                ]
            ),
            RewardSet(
                rewards=[
                    RewardProbability(
                        category=RewardType.ZONE,
                        rarity=RewardRarity.COMMON
                    )
                ]
            )
        ]
    },
    RewardReason.COMPLETE_OBJECTIVE: {
        'static': RewardSet(rewards=[
            RewardProbability(RewardType.NEEDS, RewardRarity.RARE),
            RewardProbability(RewardType.ZONE, RewardRarity.RARE),
            RewardProbability(RewardType.POINTS, RewardRarity.RARE),
        ]),
        'boxes': [
            RewardSet(
                rewards=[
                    RewardProbability(RewardType.AVATAR, RewardRarity.RARE),
                    RewardProbability(RewardType.DECORATION, RewardRarity.COMMON),
                ]
            ),
            RewardSet(
                rewards=[
                    RewardProbability(RewardType.DECORATION, RewardRarity.RARE),
                    RewardProbability(RewardType.AVATAR, RewardRarity.COMMON),
                ]
            ),
            RewardSet(
                rewards=[
                    RewardProbability(RewardType.DECORATION, RewardRarity.RARE),
                    RewardProbability(RewardType.AVATAR, RewardRarity.RARE),
                ]
            ),
        ]
    }
}


class RewardsFactory:
    @staticmethod
    def get_reward_token_by_reason(authorizer: Authorizer, area: Optional[str], reason: RewardReason):
        rewards = REWARDS_BY_REASON[reason]
        token = RewardsService.generate_reward_token(authorizer=authorizer, static=rewards['static'],
                                                     boxes=rewards['boxes'], reason=reason, area=area)
        return token
