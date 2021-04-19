import pytest
from botocore.stub import Stubber
from flask import json
from schema import Schema

from ..app import *


@pytest.fixture(scope="function")
def ddb_stubber():
    # noinspection PyProtectedMember
    ddb_stubber = Stubber(BeneficiariesService.get_interface()._model.get_table().meta.client)
    ddb_stubber.activate()
    yield ddb_stubber
    ddb_stubber.deactivate()


def test_get_avatar(ddb_stubber: Stubber):
    ddb_stubber.add_response('get_item', {
        'Item': {
            'avatar': {
                'M': {}
            }
        }
    }, {'TableName': 'beneficiaries',
        'Key': {'user': 'user-sub'},
        'ProjectionExpression': 'avatar',
        })

    response = get_avatar(HTTPEvent({
        'pathParameters': {
            'sub': 'user-sub'
        }
    }))
    assert response.status == 200
    Schema({
        'bottom': None,
        'left_eye': None,
        'mouth': None,
        'right_eye': None,
        'top': None,
        'neckerchief': None
    }).validate(response.body)


def test_update_avatar(ddb_stubber: Stubber):
    get_params = {
        'RequestItems': {
            'logs': {
                'Keys': [
                    {
                        'tag': 'REWARD::AVATAR::1',
                        'user': 'user-sub'
                    },
                    {
                        'tag': 'REWARD::AVATAR::2',
                        'user': 'user-sub'
                    },
                    {
                        'tag': 'REWARD::AVATAR::4',
                        'user': 'user-sub'
                    },
                ],
                'AttributesToGet': ['data', 'tag'],
            }
        }
    }

    ddb_stubber.add_response('batch_get_item', {
        'Responses': {
            'logs': [
                {
                    'data': {
                        'M': {
                            'category': {'S': 'AVATAR'},
                            'release': {'N': str(0)},
                            'id': {'N': str(1)},
                            'rarity': {'S': 'COMMON'},
                            'description': {
                                'M': {
                                    'description': {
                                        'M': {'description': {'M': {}}}
                                    }
                                }
                            }
                        }
                    },
                    'tag': {'S': "REWARD::AVATAR::1"}
                },
                {
                    'data': {
                        'M': {
                            'category': {'S': 'AVATAR'},
                            'release': {'N': str(0)},
                            'id': {'N': str(2)},
                            'rarity': {'S': 'COMMON'},
                            'description': {
                                'M': {
                                    'description': {
                                        'M': {'description': {'M': {}}}
                                    }
                                }
                            }
                        }
                    },
                    'tag': {'S': "REWARD::AVATAR::2"}
                },
                {
                    'data': {
                        'M': {
                            'category': {'S': 'AVATAR'},
                            'release': {'N': str(0)},
                            'id': {'N': str(4)},
                            'rarity': {'S': 'COMMON'},
                            'description': {
                                'M': {
                                    'description': {
                                        'M': {'description': {'M': {}}}
                                    }
                                }
                            }
                        }
                    },
                    'tag': {'S': "REWARD::AVATAR::4"}
                }
            ]
        }
    }, get_params)
    ddb_stubber.add_response('update_item',
                             {},
                             {'ExpressionAttributeNames': {'#attr_avatar': 'avatar'},
                              'ExpressionAttributeValues': {
                                  ':val_avatar': {
                                      'bottom': {
                                          'category': 'AVATAR',
                                          'description': {'description': {'description': {}}},
                                          'id': 4,
                                          'rarity': 'COMMON',
                                          'release': 0
                                      },
                                      'left_eye': {
                                          'category': 'AVATAR',
                                          'description': {'description': {'description': {}}},
                                          'id': 1,
                                          'rarity': 'COMMON',
                                          'release': 0
                                      },
                                      'mouth': {
                                          'category': 'AVATAR',
                                          'description': {'description': {'description': {}}},
                                          'id': 2,
                                          'rarity': 'COMMON',
                                          'release': 0
                                      },
                                      'right_eye': {
                                          'category': 'AVATAR',
                                          'description': {'description': {'description': {}}},
                                          'id': 1,
                                          'rarity': 'COMMON',
                                          'release': 0
                                      },
                                      'top': None,
                                      'neckerchief': None
                                  }},
                              'Key': {'user': 'user-sub'},
                              'ReturnValues': 'UPDATED_NEW',
                              'TableName': 'beneficiaries',
                              'UpdateExpression': 'SET #attr_avatar=:val_avatar'})

    response = update_avatar(HTTPEvent({
        "requestContext": {
            "authorizer": {
                "claims": {"sub": 'user-sub'}
            }
        },
        'pathParameters': {
            'sub': 'user-sub'
        },
        'body': json.dumps({
            'left_eye': 1,
            'right_eye': 1,
            'mouth': 2,
            'top': None,
            'bottom': 4,
            'neckerchief': None
        })
    }))
    assert response.status == 200
