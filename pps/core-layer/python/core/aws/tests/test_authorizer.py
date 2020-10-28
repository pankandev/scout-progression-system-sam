from datetime import datetime

import pytest
from dateutil.relativedelta import relativedelta

from ..event import Authorizer


@pytest.fixture
def beneficiary_authorizer():
    return Authorizer({
        "claims": {
            "sub": "user-sub",
            "cognito:groups": ["Beneficiaries"],
            "email_verified": True,
            "birthdate": (datetime.now() - relativedelta(years=10, day=1)).strftime("%d-%m-%Y"),
            "iss": "https://example.com/",
            "cognito:username": "cognito-username",
            "middle_name": "Middle",
            "aud": "user-aud",
            "event_id": "event-id",
            "token_use": "id",
            "auth_time": datetime.now().timestamp(),
            "name": "Name",
            "nickname": "The User",
            "exp": datetime.now().timestamp() + 3600,
            "iat": datetime.now().timestamp(),
            "family_name": "LastName",
            "email": "user@email.com"
        }
    })


def test_age(beneficiary_authorizer: Authorizer):
    assert beneficiary_authorizer.age == 10
