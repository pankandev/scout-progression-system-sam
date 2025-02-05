import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import jwt
import pytest
from boto3.dynamodb.conditions import Key, Attr
from botocore.stub import Stubber, ANY
from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from core.services.objectives import ObjectivesService
from ..app import *


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(TasksService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_list_user_tasks(ddb_stubber: Stubber):
    params = {
        'KeyConditionExpression': Key('user').eq('user-sub'),
        'TableName': 'tasks',
        'ProjectionExpression': '#attr_objective, #attr_original_objective, '
                                '#attr_personal_objective, #attr_completed, '
                                '#attr_tasks, #attr_user',
        'ExpressionAttributeNames': {'#attr_completed': 'completed',
                                     '#attr_objective': 'objective',
                                     '#attr_original_objective': 'original-objective',
                                     '#attr_personal_objective': 'personal-objective',
                                     '#attr_tasks': 'tasks',
                                     '#attr_user': 'user'},
    }
    response = {}
    ddb_stubber.add_response('query', response, params)
    response = fetch_user_tasks(HTTPEvent({
        "pathParameters": {"sub": 'user-sub'},
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        }
    }))
    assert response.status == 200
    ddb_stubber.assert_no_pending_responses()


def test_list_user_stage_tasks(ddb_stubber: Stubber):
    params = {
        'KeyConditionExpression': Key('user').eq('user-sub') & Key('objective').begins_with('puberty::'),
        'TableName': 'tasks',
        'ProjectionExpression': '#attr_objective, #attr_original_objective, '
                                '#attr_personal_objective, #attr_completed, '
                                '#attr_tasks, #attr_user',
        'ExpressionAttributeNames': {'#attr_completed': 'completed',
                                     '#attr_objective': 'objective',
                                     '#attr_original_objective': 'original-objective',
                                     '#attr_personal_objective': 'personal-objective',
                                     '#attr_tasks': 'tasks',
                                     '#attr_user': 'user'},
    }
    response = {
        "Items": []
    }
    ddb_stubber.add_response('query', response, params)
    response = fetch_user_tasks(HTTPEvent({
        "pathParameters": {
            "sub": 'user-sub',
            "stage": "puberty"
        },
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": 'user-sub'
                }
            }
        }
    }))
    assert response.status == 200
    ddb_stubber.assert_no_pending_responses()


def test_list_user_area_tasks(ddb_stubber: Stubber):
    params = {
        'KeyConditionExpression': Key('user').eq('user-sub') & Key('objective').begins_with('puberty::corporality::'),
        'TableName': 'tasks',
        'ProjectionExpression': '#attr_objective, #attr_original_objective, '
                                '#attr_personal_objective, #attr_completed, '
                                '#attr_tasks, #attr_user',
        'ExpressionAttributeNames': {'#attr_completed': 'completed',
                                     '#attr_objective': 'objective',
                                     '#attr_original_objective': 'original-objective',
                                     '#attr_personal_objective': 'personal-objective',
                                     '#attr_tasks': 'tasks',
                                     '#attr_user': 'user'},
    }
    response = {
        'Items': []
    }
    ddb_stubber.add_response('query', response, params)
    response = fetch_user_tasks(HTTPEvent({
        "pathParameters": {
            "sub": 'user-sub',
            "stage": 'puberty',
            "area": 'corporality'
        },
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        }
    }))
    assert response.status == 200
    ddb_stubber.assert_no_pending_responses()


def test_get_user_task(ddb_stubber: Stubber):
    params = {
        'TableName': 'tasks',
        'Key': {
            'objective': 'puberty::spirituality::2.3',
            'user': 'user-sub'
        },
    }
    response = {
        'Item': {
            'completed': {'BOOL': False},
            'created': {'N': str(123456)},
            'objective': {'S': 'puberty::spirituality::2.3'},
            'original-objective': {'S': 'Original objective'},
            'personal-objective': {'S': 'Personal objective'},
            'tasks': {'L': []}
        }
    }
    ddb_stubber.add_response('get_item', response, params)
    response = fetch_user_tasks(HTTPEvent({
        "pathParameters": {
            "sub": 'user-sub',
            "stage": 'puberty',
            "area": 'spirituality',
            "subline": "2.3"
        },
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        }
    }))
    assert response.status == 200
    ddb_stubber.assert_no_pending_responses()


@freeze_time('2020-01-01')
def test_get_active_task(ddb_stubber: Stubber):
    params = {
        'TableName': 'beneficiaries',
        'Key': {'user': 'u-sub'},
        'ProjectionExpression': 'target'
    }
    response = {
        'Item': {
            'target': {
                'M': {
                    'completed': {'BOOL': False},
                    'created': {'N': str(int(time.time()))},
                    'objective': {'S': 'puberty::corporality::2.3'},
                    'original-objective': {'S': ObjectivesService.get('puberty', 'corporality', 2, 3)},
                    'personal-objective': {'S': 'A new task'},
                    'tasks': {'L': [
                        {'M': {
                            'completed': {'BOOL': False},
                            'description': {'S': 'Sub-task 1'},
                        }},
                        {'M': {
                            'completed': {'BOOL': False},
                            'description': {'S': 'Sub-task 2'}
                        }}
                    ]}
                }
            }
        }
    }
    ddb_stubber.add_response('get_item', response, params)

    timestamp = str(int(time.time()) * 1000 - 24 * 60 * 60 * 1000 - 1)
    ddb_stubber.add_response('query', {
        'Items': [
            {
                'user': {'S': 'u-sub'},
                'tag': {'S': 'STATS::PROGRESS::PUBERTY::CORPORALITY::2.3::' + str(timestamp)},
                'timestamp': {'N': timestamp},
                'log': {'S': 'A log!'},
            }
        ]
    }, {
                                 'KeyConditionExpression': Key('user').eq('u-sub') & Key('tag').begins_with(
                                     'STATS::PROGRESS::PUBERTY::CORPORALITY::2.3::'),
                                 'Limit': 1,
                                 'ScanIndexForward': False,
                                 'TableName': 'logs'
                             })
    response = get_user_active_task(HTTPEvent({
        "pathParameters": {
            "sub": 'u-sub',
            "stage": 'puberty',
            "area": 'sociability',
            "subline": "2.3"
        },
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'u-sub'}
            }
        }
    }))
    ddb_stubber.assert_no_pending_responses()

    assert response.status == 200
    Schema({
        'area': 'corporality',
        'stage': 'puberty',
        'line': 2,
        'subline': 3,
        'completed': False,
        'created': 1577836800,
        'objective': 'puberty::corporality::2.3',
        'original-objective': 'Trato de superar las dificultades físicas propias de mi crecimiento.',
        'personal-objective': 'A new task',
        'tasks': [
            {
                'completed': False,
                'description': 'Sub-task 1'
            },
            {
                'completed': False,
                'description': 'Sub-task 2'
            }
        ],
        'eligible_for_progress_reward': True,
        'score': 80,
        'token': str
    }).validate(response.body)
    decoded = jwt.JWT().decode(response.body['token'], do_verify=False)
    assert Schema({
        'sub': 'u-sub',
        'iat': 1577836800,
        'exp': 1577836800 + 1 * 24 * 60 * 60,
        'objective': 'puberty::corporality::2.3'
    }).validate(decoded)


@freeze_time("2020-01-01")
def test_start_task(ddb_stubber: Stubber):
    now = datetime.now(timezone.utc)
    now = int(now.timestamp() * 1000)

    params = {
        'TableName': 'beneficiaries',
        'Key': {'user': 'user-sub'},
        'ReturnValues': 'UPDATED_NEW',
        'ConditionExpression': '#attr_target = :val_target_condition',
        'UpdateExpression': 'SET #attr_target=:val_target',
        'ExpressionAttributeNames': {
            '#attr_target': 'target'
        },
        'ExpressionAttributeValues': {
            ':val_target_condition': None,
            ':val_target': {
                'completed': False,
                'created': now,
                'objective': 'puberty::corporality::2.3',
                'original-objective': ObjectivesService.get('puberty', 'corporality', 2, 3),
                'personal-objective': 'A new task',
                'score': 80,
                'tasks': [
                    {
                        'completed': False,
                        'description': 'Sub-task 1',
                    },
                    {
                        'completed': False,
                        'description': 'Sub-task 2'
                    }
                ]
            }
        }
    }
    response = {}
    ddb_stubber.add_response('update_item', response, params)
    with patch('time.time', lambda: now):
        start_task(HTTPEvent({
            "pathParameters": {
                "sub": 'user-sub',
                "stage": 'puberty',
                "area": 'corporality',
                "subline": "2.3"
            },
            "body": json.dumps({
                "description": "A new task",
                "sub-tasks": ["Sub-task 1", "Sub-task 2"]
            }),
            "requestContext": {
                "authorizer": {
                    "claims": {"sub": 'user-sub'}
                }
            }
        }))
    ddb_stubber.assert_no_pending_responses()


def test_update_task(ddb_stubber: Stubber):
    params = {
        'TableName': 'beneficiaries',
        'Key': {'user': 'user-sub'},
        'ReturnValues': 'UPDATED_NEW',
        'UpdateExpression': 'SET #attr_target.#attr_target_personal_objective=:val_target_personal_objective, '
                            '#attr_target.#attr_target_tasks=:val_target_tasks',
        'ExpressionAttributeNames': {
            '#attr_target': 'target',
            '#attr_target_personal_objective': 'personal-objective',
            '#attr_target_tasks': 'tasks',
        },
        'ExpressionAttributeValues': {
            ':val_target_tasks': [
                {
                    'completed': True,
                    'description': 'Sub-task 1',
                },
                {
                    'completed': False,
                    'description': 'Sub-task 2'
                }
            ],
            ':val_target_personal_objective': 'A new task'
        }
    }
    response = {
        "Attributes": {
            "target": {
                'M': {
                    'tasks': {'L': [
                        {
                            'M': {
                                'completed': {'BOOL': True},
                                'description': {'S': 'Sub-task 1'},
                            }
                        },
                        {
                            'M': {
                                'completed': {'BOOL': False},
                                'description': {'S': 'Sub-task 2'}
                            }
                        }
                    ]},
                    'personal-objective': {'S': 'A new task'}
                }
            }
        }
    }
    ddb_stubber.add_response('update_item', response, params)
    update_active_task(HTTPEvent({
        "pathParameters": {
            "sub": 'user-sub',
            "stage": 'puberty',
            "area": 'corporality',
            "subline": "2.3"
        },
        "body": json.dumps({
            "description": "A new task",
            "sub-tasks": [{
                "description": "Sub-task 1",
                "completed": True
            }, {
                "description": "Sub-task 2",
                "completed": False
            }]
        }),
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        }
    }))
    ddb_stubber.assert_no_pending_responses()


@freeze_time('2020-01-01')
def test_complete_task(ddb_stubber: Stubber):
    now = int(time.time())

    get_params = {
        'Key': {'user': 'user-sub'},
        'ProjectionExpression': 'target',
        'TableName': 'beneficiaries'
    }

    get_response = {
        'Item': {
            'user': {'S': 'abcABC1234'},
            'group': {'S': 'district::group'},
            'unit-user': {'S': 'unit::abcABC12345'},
            'full-name': {'S': 'Name'},
            'nickname': {'S': 'Name'},
            'birthdate': {'S': '01-01-2001'},
            'score': {'M': {}},
            'n_tasks': {'M': {}},
            'bought_items': {'M': {}},
            'set_base_tasks': {'BOOL': False},
            'target': {
                'M': {
                    'original-objective': {'S': 'Original'},
                    'personal-objective': {'S': 'Personal'},
                    'objective': {'S': 'puberty::corporality::2.1'},
                    'score': {'N': str(0)}
                }
            }
        }
    }

    beneficiary_update_params = {
        'TableName': 'beneficiaries',
        'Key': {'user': 'user-sub'},
        'ReturnValues': 'UPDATED_OLD',
        'UpdateExpression': 'SET #attr_target=:val_target ADD #attr_score.#attr_score_corporality :val_score_corporality, '
                            '#attr_n_tasks.#attr_n_tasks_corporality :val_n_tasks_corporality',
        'ExpressionAttributeNames': {
            '#attr_score': 'score',
            '#attr_n_tasks': 'n_tasks',
            '#attr_n_tasks_corporality': 'corporality',
            '#attr_score_corporality': 'corporality',
            '#attr_target': 'target',
        },
        'ConditionExpression': Attr('target').ne(None),
        'ExpressionAttributeValues': {
            ':val_target': None,
            ':val_n_tasks_corporality': 1,
            ':val_score_corporality': 80
        }
    }
    beneficiary_update_response = {
        "Attributes": {
            'n_tasks': {
                'M': {
                    'corporality': {'N': str(2)}  # this is one less than its current value
                }
            },
            "target": {
                'M': {
                    'tasks': {'L': [
                        {
                            'M': {
                                'completed': {'BOOL': True},
                                'description': {'S': 'Sub-task 1'},
                            }
                        },
                        {
                            'M': {
                                'completed': {'BOOL': True},
                                'description': {'S': 'Sub-task 2'}
                            }
                        }
                    ]},
                    'personal-objective': {'S': 'A new task'},
                    'created': {'N': str(now)},
                    'objective': {'S': 'puberty::corporality::2.1'},
                    'original-objective': {'S': ObjectivesService.get('puberty', 'corporality', 2, 1)},
                }
            }
        }
    }

    tasks_params = {
        'TableName': 'tasks',
        'ReturnValues': 'NONE',
        'Item': {
            'completed': True,
            'created': ANY,
            'objective': 'puberty::corporality::2.1',
            'original-objective': ANY,
            'personal-objective': 'A new task',
            'tasks': [{'completed': True, 'description': 'Sub-task 1'},
                      {'completed': True, 'description': 'Sub-task 2'}],
            'user': 'user-sub',
        }
    }

    tasks_response = {
        'Attributes': {
            'created': {'N': str(time.time())},
            'objective': {'S': 'puberty::corporality::2.1'},
            'original-objective': {'S': 'Original'},
            'personal-objective': {'S': 'A new task'},
            'tasks': {'L': [{'M': {'completed': {'BOOL': True}, 'description': {'S': 'Sub-task 1'}}},
                      {'M': {'completed': {'BOOL': True}, 'description': {'S': 'Sub-task 2'}}}]},
            'user': {'S': 'user-sub'},
        }
    }

    update_response = {
        'Attributes': {
            'generated_token_last': {'N': str(10)}
        }
    }

    update_params = {
        'ExpressionAttributeNames': {'#attr_generated_token_last': 'generated_token_last'},
        'ExpressionAttributeValues': {':val_generated_token_last': 1},
        'Key': {'user': 'user-sub'},
        'ReturnValues': 'UPDATED_NEW',
        'TableName': 'beneficiaries',
        'UpdateExpression': 'ADD #attr_generated_token_last :val_generated_token_last'
    }
    logs_params = {
        'TableName': 'logs',
        'ReturnValues': 'NONE',
        'Item': {
            'tag': 'STATS::COMPLETED::PUBERTY::CORPORALITY::2.1',
            'log': 'Completed an objective!',
            'data': {},
            'timestamp': 1577836800000,
            'user': 'user-sub'
        }
    }

    logs_response = {}

    ddb_stubber.add_response('get_item', get_response, get_params)
    ddb_stubber.add_response('update_item', beneficiary_update_response, beneficiary_update_params)
    ddb_stubber.add_response('put_item', tasks_response, tasks_params)
    ddb_stubber.add_response('update_item', update_response, update_params)
    ddb_stubber.add_response('put_item', logs_response, logs_params)

    response = complete_active_task(HTTPEvent({
        "pathParameters": {
            "sub": 'user-sub'
        },
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        }
    }))
    assert response.status == 200
    Schema({
        'message': 'Completed task',
        'task': {
            'tasks': [
                {'completed': True, 'description': 'Sub-task 1'},
                {'completed': True, 'description': 'Sub-task 2'},
            ],
            'personal-objective': 'A new task',
            'created': Decimal(now),
            'objective': 'puberty::corporality::2.1',
            'original-objective': 'Comprendo que los cambios que se estan '
                                  'produciendo en mi cuerpo influyen en mi manera de ser.',
            'completed': True,
        },
        'reward': str
    }).validate(response.body)
    reward_token = response.body['reward']
    decoded = jwt.JWT().decode(reward_token, do_verify=False)
    Schema({
        'index': 10,
        'sub': 'user-sub',
        'iat': 1577836800,
        'exp': 1577836800 + 7 * 24 * 60 * 60,
        'area': 'corporality',
        'reason': 'COMPLETE_OBJECTIVE',
        'static': [
            {'type': 'NEEDS', 'rarity': 'RARE'},
            {'type': 'ZONE', 'rarity': 'RARE'},
            {'type': 'POINTS', 'rarity': 'RARE'},
        ],
        'boxes': [
            [{'type': 'AVATAR', 'rarity': 'RARE'},
             {'type': 'DECORATION', 'rarity': 'COMMON'}],
            [{'type': 'DECORATION', 'rarity': 'RARE'},
             {'type': 'AVATAR', 'rarity': 'COMMON'}],
            [{'type': 'AVATAR', 'rarity': 'RARE'},
             {'type': 'DECORATION', 'rarity': 'RARE'}]
        ]
    }).validate(decoded)
    ddb_stubber.assert_no_pending_responses()


@freeze_time("2020-01-01")
def test_initialize(ddb_stubber: Stubber):
    now = 1577836800000
    user_sub = 'userABC123'

    update_response = {
        'Attributes': {
            'generated_token_last': {'N': str(10)}
        }
    }

    update_params = {
        'ExpressionAttributeNames': {'#attr_generated_token_last': 'generated_token_last'},
        'ExpressionAttributeValues': {':val_generated_token_last': 1},
        'Key': {'user': 'userABC123'},
        'ReturnValues': 'UPDATED_NEW',
        'TableName': 'beneficiaries',
        'UpdateExpression': 'ADD #attr_generated_token_last :val_generated_token_last'
    }

    batch_params = {
        'RequestItems': {
            'tasks': [
                {
                    'PutRequest': {
                        'Item': {
                            'completed': True,
                            'created': now,
                            'objective': 'prepuberty::corporality::1.1',
                            'original-objective': 'Participo en actividades que me ayudan a mantener mi cuerpo fuerte y sano.',
                            'personal-objective': None,
                            'score': 0,
                            'tasks': [],
                            'user': user_sub
                        },
                    }
                },
                {
                    'PutRequest': {
                        'Item': {
                            'completed': True,
                            'created': now,
                            'objective': 'prepuberty::character::2.3',
                            'original-objective': 'Me ofrezco para ayudar en mi patrulla y en mi casa.',
                            'personal-objective': None,
                            'score': 0,
                            'tasks': [],
                            'user': user_sub
                        },
                    }
                },
            ]
        }
    }
    batch_response = {}

    ben_params = {
        'ConditionExpression': Attr('set_base_tasks').eq(False),
        'ExpressionAttributeNames': {'#attr_set_base_tasks': 'set_base_tasks'},
        'ExpressionAttributeValues': {':val_set_base_tasks': True},
        'Key': {'user': 'userABC123'},
        'ReturnValues': 'UPDATED_NEW',
        'TableName': 'beneficiaries',
        'UpdateExpression': 'SET #attr_set_base_tasks=:val_set_base_tasks'
    }

    ben_response = {}
    ddb_stubber.add_response('batch_write_item', batch_response, batch_params)
    ddb_stubber.add_response('update_item', ben_response, ben_params)
    ddb_stubber.add_response('update_item', update_response, update_params)

    with patch('time.time', lambda: now):
        response = initialize_tasks(HTTPEvent(
            event={
                "pathParameters": {
                    "sub": 'userABC123'
                },
                "requestContext": {
                    "authorizer": {
                        "claims": {
                            'sub': 'userABC123',
                            'birthdate': (datetime.now() - relativedelta(years=12, day=1)).strftime("%d-%m-%Y")
                        }
                    },
                },
                "body": json.dumps({
                    "objectives": [
                        {
                            "area": "corporality",
                            "line": 1,
                            "subline": 1
                        },
                        {
                            "area": "character",
                            "line": 2,
                            "subline": 3
                        }
                    ]
                })
            },
        ))
        assert response.status == 200
    ddb_stubber.assert_no_pending_responses()
