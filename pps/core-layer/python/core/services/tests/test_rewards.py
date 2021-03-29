import jwt
import pytest
import schema
from botocore.stub import Stubber
from freezegun import freeze_time

from core.aws.event import Authorizer
from core.services.logs import LogsService
from core.services.rewards import RewardsService, RewardSet, Reward, RewardType


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(LogsService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


@freeze_time('2020-01-01')
def test_reward_token():
    authorizer = Authorizer({
        "claims": {
            "sub": "abcABC123"
        }
    })

    static_rewards = RewardSet(rewards=[
        Reward(reward_type=RewardType.POINTS, description={'amount': 100}),
    ])
    box_rewards = [RewardSet(rewards=[
        Reward(reward_type=RewardType.ZONE, description={'id': 'GRASS'}),
        Reward(reward_type=RewardType.AVATAR, description={'type': 'mouth', 'id': 'w'}),
    ])]

    token = RewardsService.generate_reward_token(authorizer, static=static_rewards, boxes=box_rewards)

    decoded = jwt.JWT().decode(token, do_verify=False)

    schema.Schema({
        'sub': 'abcABC123',
        'id': str,
        'iat': 1577836800,
        'exp': 1577836800 + 60 * 60,
        'static': [
            {
                'type': 'POINTS',
                'description': {
                    'amount': 100
                }
            }
        ],
        'boxes': [[
            {
                'type': 'ZONE',
                'description': {
                    'id': 'GRASS'
                },
            },
            {
                'type': 'AVATAR',
                'description': {
                    'type': 'mouth',
                    'id': 'w',
                },
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
        Reward(reward_type=RewardType.POINTS, description={'amount': 100}),
    ])
    box_rewards = [RewardSet(rewards=[
        Reward(reward_type=RewardType.ZONE, description={'id': 'GRASS'}),
        Reward(reward_type=RewardType.AVATAR, description={'type': 'mouth', 'id': 'w'}),
    ])]

    batch_response = {

    }

    batch_params = {
        'RequestItems': {
            'logs': [
                {
                    'PutRequest': {
                        'Item': {
                            'tag': {
                                'S': 'REWARD',
                            },
                            'timestamp': {
                                'N': str(1577836800),
                            },
                            'log': {'S': 'Won a reward'},
                            'data': {'M': {
                                'type': 'POINTS',
                                'description': {'amount': 100}
                            }}
                        }
                    }
                },
                {
                    'PutRequest': {
                        'Item': {
                            'tag': {
                                'S': 'REWARD',
                            },
                            'timestamp': {
                                'N': str(1577836800),
                            },
                            'log': {'S': 'Won a reward'},
                            'data': {'M': {
                                'type': 'ZONE',
                                'description': {'id': 'GRASS'}
                            }}
                        }
                    }
                },
                {
                    'PutRequest': {
                        'Item': {
                            'tag': {
                                'S': 'REWARD',
                            },
                            'timestamp': {
                                'N': str(1577836800),
                            },
                            'log': {'S': 'Won a reward'},
                            'data': {'M': {
                                'type': 'AVATAR',
                                'description': {'type': 'mouth', 'id': 'w'}
                            }}
                        }
                    }
                }
            ]}
    }

    ddb_stubber.add_response('batch_write_item', batch_response, batch_params)
    token = RewardsService.generate_reward_token(authorizer, static=static_rewards, boxes=box_rewards)
    RewardsService.claim_reward(authorizer=authorizer, reward_token=token, box_index=0)
