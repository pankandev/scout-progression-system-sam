import json
from unittest.mock import patch

import jwt
import pytest
import schema
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber
from freezegun import freeze_time

from core.aws.event import Authorizer
from core.services.logs import LogsService
from core.services.rewards import RewardsService, RewardSet, Reward, RewardType, RewardProbability, RewardRarity


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(LogsService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


@freeze_time('2020-01-01')
def test_reward_token(ddb_stubber: Stubber):
    authorizer = Authorizer({
        "claims": {
            "sub": "abcABC123"
        }
    })

    static_rewards = RewardSet(rewards=[
        RewardProbability(reward_type=RewardType.POINTS, rarity=RewardRarity.COMMON),
    ])
    box_rewards = [RewardSet(rewards=[
        RewardProbability(reward_type=RewardType.ZONE, rarity=RewardRarity.RARE),
        RewardProbability(reward_type=RewardType.AVATAR, rarity=RewardRarity.RARE),
    ])]

    update_params = {
        'TableName': 'beneficiaries',
        'Key': {'user': 'abcABC123'},
        'ExpressionAttributeNames': {'#attr_generated_token_last': 'generated_token_last'},
        'ExpressionAttributeValues': {':val_generated_token_last': 1},
        'UpdateExpression': 'ADD #attr_generated_token_last :val_generated_token_last',
        'ReturnValues': 'UPDATED_NEW'
    }
    update_response = {
        'Attributes': {
            'generated_token_last': {'N': str(10)}
        }
    }
    ddb_stubber.add_response('update_item', update_response, update_params)
    token = RewardsService.generate_reward_token(authorizer, static=static_rewards, boxes=box_rewards)
    ddb_stubber.assert_no_pending_responses()

    decoded = jwt.JWT().decode(token, do_verify=False)

    schema.Schema({
        'sub': 'abcABC123',
        'index': 10,
        'iat': 1577836800,
        'exp': 1577836800 + 7 * 24 * 60 * 60,
        'static': [
            {
                'type': 'POINTS',
                'rarity': 'COMMON'
            }
        ],
        'boxes': [[
            {
                'type': 'ZONE',
                'rarity': 'RARE'
            },
            {
                'type': 'AVATAR',
                'rarity': 'RARE'
            }
        ]]
    }).validate(decoded)


@freeze_time('2020-01-01')
def test_claim_reward(ddb_stubber: Stubber):
    authorizer = Authorizer({
        "claims": {
            "sub": "abcABC123"
        }
    })
    static_rewards = RewardSet(rewards=[
        RewardProbability(reward_type=RewardType.POINTS, rarity=RewardRarity.COMMON),
    ])
    box_rewards = [RewardSet(rewards=[
        RewardProbability(reward_type=RewardType.POINTS, rarity=RewardRarity.COMMON),
        RewardProbability(reward_type=RewardType.ZONE, rarity=RewardRarity.RARE),
        RewardProbability(reward_type=RewardType.AVATAR, rarity=RewardRarity.RARE),
    ])]

    update_response = {
        'Attributes': {
            'generated_token_last': {'N': str(10)}
        }
    }

    update_params = {
        'ExpressionAttributeNames': {'#attr_generated_token_last': 'generated_token_last'},
        'ExpressionAttributeValues': {':val_generated_token_last': 1},
        'Key': {'user': 'abcABC123'},
        'ReturnValues': 'UPDATED_NEW',
        'TableName': 'beneficiaries',
        'UpdateExpression': 'ADD #attr_generated_token_last :val_generated_token_last'
    }

    ddb_stubber.add_response('update_item', update_response, update_params)

    update_response = {
        'Attributes': {
            'n_claimed_tokens': {'N': str(10)}
        }
    }

    update_params = {
        'ConditionExpression': '#attr_n_claimed_tokens < :val_n_claimed_tokens',
        'ExpressionAttributeNames': {'#attr_n_claimed_tokens': 'n_claimed_tokens'},
        'ExpressionAttributeValues': {':val_n_claimed_tokens': 10},
        'Key': {'user': 'abcABC123'},
        'ReturnValues': 'UPDATED_NEW',
        'TableName': 'beneficiaries',
        'UpdateExpression': 'SET #attr_n_claimed_tokens=:val_n_claimed_tokens'
    }

    ddb_stubber.add_response('update_item', update_response, update_params)


    for reward in static_rewards.rewards + box_rewards[0].rewards:
        if reward.type == RewardType.POINTS:
            continue
        response = {
            'Items': [
                {
                    'category': {
                        'S': reward.type.name
                    },
                    'description': {
                        'S': 'A description'
                    },
                    'release-id': {
                        'N': str(-12345 if reward.rarity == RewardRarity.RARE else 12345)
                    }
                }
            ]
        }
        lowest = 0
        highest = -99999 if reward.rarity == RewardRarity.RARE else 99999
        params = {
            'ExpressionAttributeNames': {'#attr_category': 'category',
                                         '#attr_description': 'description',
                                         '#attr_price': 'price',
                                         '#attr_release_id': 'release-id'},
            'KeyConditionExpression':
                Key('category').eq(reward.type.name) & Key('release-id').between(min(lowest, highest),
                                                                                 max(lowest, highest)),
            'Limit': 1,
            'ProjectionExpression': '#attr_category, #attr_description, #attr_release_id, #attr_price',
            'TableName': 'rewards'
        }
        ddb_stubber.add_response('query', response, params)

    batch_response = {

    }

    batch_params = {
        'RequestItems': {
            'logs': [
                {
                    'PutRequest': {
                        'Item': {
                            'tag': 'abcABC123::REWARD::POINTS',
                            'timestamp': 1577836800,
                            'log': 'Won a reward',
                            'data': {
                                'category': 'POINTS',
                                'description': {
                                    'amount': 100
                                },
                                'rarity': 'COMMON',
                                'release': 0
                            }
                        }
                    }
                },
                {
                    'PutRequest': {
                        'Item': {
                            'tag': 'abcABC123::REWARD::POINTS',
                            'timestamp': 1577836801,
                            'log': 'Won a reward',
                            'data': {
                                'category': 'POINTS',
                                'rarity': 'COMMON',
                                'release': 0,
                                'description': {
                                    'amount': 100
                                }
                            }
                        }
                    }
                },
                {
                    'PutRequest': {
                        'Item': {
                            'tag': 'abcABC123::REWARD::ZONE',
                            'timestamp': 1577836802,
                            'log': 'Won a reward',
                            'data': {
                                'category': 'ZONE',
                                'rarity': 'RARE',
                                'description': 'A description',
                                'id': 12345,
                                'release': 1,
                            }
                        }
                    }
                },
                {
                    'PutRequest': {
                        'Item': {
                            'tag': 'abcABC123::REWARD::AVATAR',
                            'timestamp': 1577836803,
                            'log': 'Won a reward',
                            'data': {
                                'category': 'AVATAR',
                                'rarity': 'RARE',
                                'id': 12345,
                                'release': 1,
                                'description': 'A description'
                            }
                        }
                    }
                }
            ]}
    }

    ddb_stubber.add_response('batch_write_item', batch_response, batch_params)

    token = RewardsService.generate_reward_token(authorizer, static=static_rewards, boxes=box_rewards)
    with patch('random.randint', lambda a, b: 0 if a < 0 else b):
        rewards = RewardsService.claim_reward(authorizer=authorizer, reward_token=token, release=1, box_index=0)
        api_map = [r.to_api_map() for r in rewards]
        schema.Schema({
            'category': 'POINTS',
            'release': 0,
            'rarity': 'COMMON',
            'description': {
                'amount': 100
            }
        }).validate(api_map[0])
        schema.Schema({
            'category': 'POINTS',
            'release': 0,
            'rarity': 'COMMON',
            'description': {
                'amount': 100
            }
        }).validate(api_map[1])
        schema.Schema({
            'category': 'ZONE',
            'release': 1,
            'rarity': 'RARE',
            'description': 'A description',
            'id': 12345
        }).validate(api_map[2])
        schema.Schema({
            'category': 'AVATAR',
            'release': 1,
            'rarity': 'RARE',
            'description': 'A description',
            'id': 12345
        }).validate(api_map[3])

    ddb_stubber.assert_no_pending_responses()


def test_get_random(ddb_stubber: Stubber):
    params = {
        'KeyConditionExpression': Key('category').eq('AVATAR') & Key('release-id').between(0, 99999),
        'ProjectionExpression': '#attr_category, #attr_description, #attr_release_id, #attr_price',
        'ExpressionAttributeNames': {
            '#attr_category': 'category',
            '#attr_description': 'description',
            '#attr_price': 'price',
            '#attr_release_id': 'release-id'
        },
        'Limit': 1,
        'TableName': 'rewards'}
    response = {
        'Items': [
            {
                'category': {
                    'S': 'AVATAR'
                },
                'description': {
                    'S': 'A description'
                },
                'release-id': {
                    'N': str(112345)
                }
            }
        ]
    }
    ddb_stubber.add_response('query', response, params)
    with patch('random.randint', lambda a, b: b):
        reward = RewardsService.get_random(RewardType.AVATAR, 1, RewardRarity.COMMON)
    assert reward.release == 2
    assert reward.id == 12345
    assert reward.type == RewardType.AVATAR
    assert reward.description == 'A description'
    ddb_stubber.assert_no_pending_responses()
