import time
from datetime import datetime
from unittest.mock import patch

import pytest
from boto3.dynamodb.conditions import Key, Attr
from botocore.stub import Stubber, ANY
from dateutil.relativedelta import relativedelta

from core.aws.event import Authorizer
from core.services.beneficiaries import BeneficiariesService
from core.services.objectives import ObjectivesService
from core.services.tasks import ObjectiveKey
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
        'ProjectionExpression': '#attr_objective_description, #attr_completed, #attr_tasks',
        'ExpressionAttributeNames': {'#attr_completed': 'completed',
                                     '#attr_objective_description': 'objective-description',
                                     '#attr_tasks': 'tasks'},
    }
    response = {}
    ddb_stubber.add_response('query', response, params)
    list_user_tasks(HTTPEvent({
        "pathParameters": {"sub": 'user-sub'},
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        }
    }))
    ddb_stubber.assert_no_pending_responses()


def test_list_user_stage_tasks(ddb_stubber: Stubber):
    params = {
        'KeyConditionExpression': Key('user').eq('user-sub') & Key('objective').begins_with('puberty::'),
        'TableName': 'tasks',
        'ProjectionExpression': '#attr_objective_description, #attr_completed, #attr_tasks',
        'ExpressionAttributeNames': {'#attr_completed': 'completed',
                                     '#attr_objective_description': 'objective-description',
                                     '#attr_tasks': 'tasks'},
    }
    response = {}
    ddb_stubber.add_response('query', response, params)
    list_user_stage_tasks(HTTPEvent({
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
    ddb_stubber.assert_no_pending_responses()


def test_list_user_area_tasks(ddb_stubber: Stubber):
    params = {
        'KeyConditionExpression': Key('user').eq('user-sub') & Key('objective').begins_with('puberty::an-area::'),
        'TableName': 'tasks',
        'ProjectionExpression': '#attr_objective_description, #attr_completed, #attr_tasks',
        'ExpressionAttributeNames': {'#attr_completed': 'completed',
                                     '#attr_objective_description': 'objective-description',
                                     '#attr_tasks': 'tasks'},
    }
    response = {}
    ddb_stubber.add_response('query', response, params)
    list_user_area_tasks(HTTPEvent({
        "pathParameters": {
            "sub": 'user-sub',
            "stage": 'puberty',
            "area": 'an-area'
        },
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        }
    }))
    ddb_stubber.assert_no_pending_responses()


def test_get_user_task(ddb_stubber: Stubber):
    params = {
        'TableName': 'tasks',
        'Key': {
            'objective': 'puberty::spirituality::2.3',
            'user': 'user-sub'
        },
    }
    response = {}
    ddb_stubber.add_response('get_item', response, params)
    get_user_task(HTTPEvent({
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
    ddb_stubber.assert_no_pending_responses()


def test_get_active_task(ddb_stubber: Stubber):
    params = {
        'TableName': 'beneficiaries',
        'Key': {'user': 'user-sub'},
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
    get_user_active_task(HTTPEvent({
        "pathParameters": {
            "sub": 'user-sub',
            "stage": 'puberty',
            "area": 'sociability',
            "subline": "2.3"
        },
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        }
    }))
    ddb_stubber.assert_no_pending_responses()


def test_start_task(ddb_stubber: Stubber):
    now = int(time.time())

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


def test_complete_task(ddb_stubber: Stubber):
    now = int(time.time())

    get_params = {
        'Key': {'user': 'user-sub'},
        'ProjectionExpression': 'target.objective',
        'TableName': 'beneficiaries'
    }

    get_response = {
        'Item': {
            'target': {
                'M': {
                    'objective': {'S': 'puberty::corporality::2.3'},
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
                    'objective': {'S': 'puberty::corporality::2.3'},
                    'original-objective': {'S': ObjectivesService.get('puberty', 'corporality', 2, 3)},
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
            'objective': 'puberty::corporality::2.3',
            'original-objective': ANY,
            'personal-objective': 'A new task',
            'tasks': [{'completed': True, 'description': 'Sub-task 1'},
                      {'completed': True, 'description': 'Sub-task 2'}],
            'user': 'user-sub',
        }
    }

    tasks_response = {

    }

    ddb_stubber.add_response('get_item', get_response, get_params)
    ddb_stubber.add_response('update_item', beneficiary_update_response, beneficiary_update_params)
    ddb_stubber.add_response('put_item', tasks_response, tasks_params)

    complete_active_task(HTTPEvent({
        "pathParameters": {
            "sub": 'user-sub'
        },
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        }
    }))
    ddb_stubber.assert_no_pending_responses()


def test_initialize(ddb_stubber: Stubber):
    now = time.time()
    user_sub = 'userABC123'
    batch_params = {
        'RequestItems': {
            'tasks': [
                {
                    'PutRequest': {
                        'Item': {
                            'completed': {'BOOL': True, },
                            'created': {'N': int(now), },
                            'objective': {'S': 'prepuberty::corporality::1.1'},
                            'original-objective': {
                                'S': 'Participo en actividades que me ayudan a mantener mi cuerpo fuerte y sano.'},
                            'personal-objective': {'NULL': True},
                            'score': {'N': 0},
                            'tasks': {'NULL': True},
                            'user': {'S': user_sub}
                        },
                    }
                },
                {
                    'PutRequest': {
                        'Item': {
                            'completed': {'BOOL': True, },
                            'created': {'N': int(now), },
                            'objective': {'S': 'prepuberty::character::2.3'},
                            'original-objective': {
                                'S': 'Me ofrezco para ayudar en mi patrulla y en mi casa.'},
                            'personal-objective': {'NULL': True},
                            'score': {'N': 0},
                            'tasks': {'NULL': True},
                            'user': {'S': user_sub}
                        },
                    }
                },
            ]
        }
    }
    batch_response = {}

    ben_params = {
        'ConditionExpression': Attr('set_base_tasks').eq(None),
        'ExpressionAttributeNames': {'#attr_set_base_tasks': 'set_base_tasks'},
        'ExpressionAttributeValues': {':val_set_base_tasks': False},
        'Key': {'user': 'userABC123'},
        'ReturnValues': 'UPDATED_NEW',
        'TableName': 'beneficiaries',
        'UpdateExpression': 'SET #attr_set_base_tasks=:val_set_base_tasks'
    }

    ben_response = {}
    ddb_stubber.add_response('batch_write_item', batch_response, batch_params)
    ddb_stubber.add_response('update_item', ben_response, ben_params)
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
