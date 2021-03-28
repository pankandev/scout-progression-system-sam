from datetime import datetime, timezone
from unittest.mock import patch

import jwt
import schema
import pytest
from boto3.dynamodb.conditions import Key
from botocore.stub import Stubber
from freezegun import freeze_time
from jwt.utils import get_int_from_datetime

from core.aws.event import Authorizer
from core.services.beneficiaries import BeneficiariesService, RewardSet, Reward, RewardType


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(BeneficiariesService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_query_group(ddb_stubber: Stubber):
    params = {
        'IndexName': 'ByGroup',
        'KeyConditionExpression': Key('group').eq('district::group'),
        'TableName': 'beneficiaries'}
    response = {}
    ddb_stubber.add_response('query', response, params)
    BeneficiariesService.query_group('district', 'group')
    ddb_stubber.assert_no_pending_responses()


def test_query_unit(ddb_stubber: Stubber):
    params = {
        'IndexName': 'ByGroup',
        'KeyConditionExpression': Key('group').eq('district::group') & Key('unit-user').begins_with('scouts::'),
        'TableName': 'beneficiaries'}
    response = {}
    ddb_stubber.add_response('query', response, params)
    BeneficiariesService.query_unit('district', 'group', 'scouts')
    ddb_stubber.assert_no_pending_responses()


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
    box_rewards = RewardSet(rewards=[
        Reward(reward_type=RewardType.ZONE, description={'id': 'GRASS'}),
        Reward(reward_type=RewardType.AVATAR, description={'type': 'mouth', 'id': 'w'}),
    ])

    token = BeneficiariesService.generate_reward_token(authorizer, static=static_rewards, box=box_rewards)

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
        'box': [
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
        ]
    }).validate(decoded)
