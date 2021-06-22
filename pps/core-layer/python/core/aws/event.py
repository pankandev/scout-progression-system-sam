import json
import os
from datetime import datetime, date
from json import JSONDecodeError
from typing import Union, List

from core.exceptions.invalid import InvalidException
from core.exceptions.unauthorized import UnauthorizedException
from core.router.environment import ENVIRONMENT
from jwt import jwt


class Authorizer:
    def __init__(self, authorizer: dict):
        claims = authorizer["claims"]
        self.sub: str = claims.get("sub")
        self.groups: str = claims.get("cognito:groups", [])
        self.email_verified: str = claims.get("email_verified")
        self.iss: str = claims.get("iss")
        self.aud: str = claims.get("aud")
        self.event_id: str = claims.get("event_id")
        self.token_use: str = claims.get("token_use")
        self.auth_time: str = claims.get("auth_time")
        self.exp: str = claims.get("exp")
        self.iat: str = claims.get("iat")

        self.email: str = claims.get("email")
        self.username: str = claims.get("cognito:username")
        self.name: str = claims.get("name")
        self.middle_name: str = claims.get("middle_name")
        self.family_name: str = claims.get("family_name")
        self.nickname: str = claims.get("nickname")
        self.unit: str = claims.get("gender")
        self.scout_groups: List[str] = [g.strip() for g in claims.get("custom:groups", '').split(',')]

        birth_date = claims.get("birthdate", '01-01-2021')
        self.birth_date: datetime = datetime.strptime(birth_date, "%d-%m-%Y")

    @property
    def is_beneficiary(self):
        return "Beneficiaries" in self.groups

    @property
    def is_scouter(self):
        return "Scouters" in self.groups

    @property
    def is_admin(self):
        return "Admin" in self.groups

    @property
    def age(self):
        if self.birth_date is None:
            raise ValueError()
        today = date.today()
        return today.year - self.birth_date.year - (
                (today.month, today.day) < (self.birth_date.month, self.birth_date.day))

    @property
    def stage(self):
        from core.services.beneficiaries import BeneficiariesService
        return BeneficiariesService.calculate_stage(self.birth_date)

    @property
    def full_name(self):
        if self.middle_name is None:
            return self.base_name
        else:
            names = [self.name, self.middle_name, self.family_name]
        return ' '.join(names)

    @property
    def base_name(self):
        names = [self.name, self.family_name]
        return ' '.join(names)


class HTTPEvent:
    def __init__(self, event: dict):
        self.body = event.get("body")
        self.resource: str = event.get("resource")
        self.method: str = event.get("httpMethod")
        self.headers: dict = event.get("headers")
        self.context: dict = event.get("requestContext", {})

        authorizer_data = HTTPEvent.get_authorizer_claims_from_token(
            self.headers.get("Authorization")) if ENVIRONMENT.is_local else self.context.get("authorizer")
        self.authorizer = Authorizer(authorizer_data) if authorizer_data else None

        params = event.get("pathParameters", {})
        self.params: dict = {} if params is None else params

        query_params = event.get("queryStringParameters", {})
        self.queryParams: dict = {} if query_params is None else query_params

    @staticmethod
    def get_authorizer_claims_from_token(token: Union[str, None]):
        if token is None:
            return None
        splitted = token.split(' ')
        if len(splitted) != 2:
            raise UnauthorizedException("Bad token")
        if splitted[0] != "Bearer":
            raise UnauthorizedException("Bad token")
        return {"claims": jwt.JWT().decode(splitted[1], do_verify=False)}

    @property
    def url(self) -> str:
        if self.headers is None or self.context is None:
            return None
        return "https://" + os.path.join(self.headers.get('Host'), self.context.get('stage'))

    @property
    def json(self):
        try:
            return json.loads(self.body)
        except JSONDecodeError:
            raise InvalidException('Body isn\'t a valid JSON data')
        except TypeError:
            raise InvalidException('Body isn\'t a valid JSON data')

    def concat_url(self, *args):
        url = self.url
        if url is None:
            url = ''
        return os.path.join(url, 'api', *args)
