from unittest.mock import patch

import pytest

import jwt
import schema
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber
from core.aws.event import Authorizer
from core.services.logs import LogsService
from core.services.rewards import RewardsService, RewardSet, RewardType, RewardProbability, RewardRarity, \
    RewardReason
from freezegun import freeze_time


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
        RewardProbability(category=RewardType.POINTS, rarity=RewardRarity.COMMON),
    ])
    box_rewards = [RewardSet(rewards=[
        RewardProbability(category=RewardType.ZONE, rarity=RewardRarity.RARE),
        RewardProbability(category=RewardType.AVATAR, rarity=RewardRarity.RARE),
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
    token = RewardsService.generate_reward_token(authorizer, static=static_rewards, boxes=box_rewards,
                                                 reason=RewardReason.PROGRESS_LOG, area='corporality')
    ddb_stubber.assert_no_pending_responses()

    decoded = jwt.JWT().decode(token, do_verify=False)

    schema.Schema({
        'sub': 'abcABC123',
        'reason': 'PROGRESS_LOG',
        'index': 10,
        'iat': 1577836800,
        'exp': 1577836800 + 7 * 24 * 60 * 60,
        'area': 'corporality',
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
        RewardProbability(category=RewardType.POINTS, rarity=RewardRarity.COMMON),
    ])
    box_rewards = [RewardSet(rewards=[
        RewardProbability(category=RewardType.POINTS, rarity=RewardRarity.COMMON),
        RewardProbability(category=RewardType.ZONE, rarity=RewardRarity.RARE),
        RewardProbability(category=RewardType.AVATAR, rarity=RewardRarity.RARE),
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
                            'user': 'abcABC123',
                            'tag': 'REWARD::POINTS::' + str(1577836800000),
                            'timestamp': 1577836800000,
                            'log': 'Won a reward',
                            'data': {
                                'category': 'POINTS',
                                'description': {
                                    'amount': 20
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
                            'user': 'abcABC123',
                            'tag': 'REWARD::POINTS::' + str(1577836800001),
                            'timestamp': 1577836800001,
                            'log': 'Won a reward',
                            'data': {
                                'category': 'POINTS',
                                'rarity': 'COMMON',
                                'release': 0,
                                'description': {
                                    'amount': 20
                                }
                            }
                        }
                    }
                },
                {
                    'PutRequest': {
                        'Item': {
                            'user': 'abcABC123',
                            'tag': 'REWARD::ZONE::12345::' + str(1577836800002),
                            'timestamp': 1577836800002,
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
                            'user': 'abcABC123',
                            'tag': 'REWARD::AVATAR::12345',
                            'timestamp': 1577836800003,
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

    ddb_stubber.add_response('update_item', {}, {
        'ExpressionAttributeNames': {
            '#attr_score': 'score',
            '#attr_score_affectivity': 'affectivity',
            '#attr_score_character': 'character',
            '#attr_score_corporality': 'corporality',
            '#attr_score_creativity': 'creativity',
            '#attr_score_sociability': 'sociability',
            '#attr_score_spirituality': 'spirituality'
        },
        'ExpressionAttributeValues': {
            ':val_score_affectivity': 7,
            ':val_score_character': 7,
            ':val_score_corporality': 7,
            ':val_score_creativity': 7,
            ':val_score_sociability': 7,
            ':val_score_spirituality': 7
        },
        'Key': {'user': 'abcABC123'},
        'ReturnValues': 'UPDATED_NEW',
        'TableName': 'beneficiaries',
        'UpdateExpression': 'ADD #attr_score.#attr_score_corporality '
                            ':val_score_corporality, '
                            '#attr_score.#attr_score_creativity '
                            ':val_score_creativity, #attr_score.#attr_score_character '
                            ':val_score_character, '
                            '#attr_score.#attr_score_affectivity '
                            ':val_score_affectivity, '
                            '#attr_score.#attr_score_sociability '
                            ':val_score_sociability, '
                            '#attr_score.#attr_score_spirituality '
                            ':val_score_spirituality'
    })

    token = RewardsService.generate_reward_token(authorizer, static=static_rewards, boxes=box_rewards)
    with patch('random.randint', lambda a, b: 0 if a < 0 else b):
        rewards = RewardsService.claim_reward(authorizer=authorizer, reward_token=token, release=1, box_index=0)
        api_map = [r.to_api_map() for r in rewards]
        schema.Schema({
            'category': 'POINTS',
            'release': 0,
            'rarity': 'COMMON',
            'description': {
                'amount': 20
            }
        }).validate(api_map[0])
        schema.Schema({
            'category': 'POINTS',
            'release': 0,
            'rarity': 'COMMON',
            'description': {
                'amount': 20
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
    assert reward.id == 112345
    assert reward.type == RewardType.AVATAR
    assert reward.description == 'A description'
    ddb_stubber.assert_no_pending_responses()
