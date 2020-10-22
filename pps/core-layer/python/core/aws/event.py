import os


class Authorizer:
    def __init__(self, authorizer: dict):
        claims = authorizer["claims"]
        self.sub: str = claims.get("sub")
        self.groups: str = claims.get("cognito:groups")
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

    @property
    def full_name(self):
        if self.middle_name is None:
            names = [self.name, self.family_name]
        else:
            names = [self.name, self.middle_name, self.family_name]
        return ' '.join(names)


class HTTPEvent:
    def __init__(self, event: dict):
        self.body = event.get("body")
        self.resource: str = event.get("resource")
        self.method: str = event.get("httpMethod")
        self.headers: dict = event.get("headers")
        self.context: dict = event.get("requestContext", {})

        authorizer_data = self.context.get("authorizer")
        print(authorizer_data)
        self.authorizer = Authorizer(authorizer_data) if authorizer_data else None

        params = event.get("pathParameters", {})
        self.params: dict = {} if params is None else params

        query_params = event.get("queryStringParameters", {})
        self.queryParams: dict = {} if query_params is None else query_params

    @property
    def url(self) -> str:
        if self.headers is None or self.context is None:
            return None
        return "https://" + os.path.join(self.headers.get('Host'), self.context.get('stage'))

    def concat_url(self, *args):
        url = self.url
        if url is None:
            url = ''
        return os.path.join(url, 'api', *args)
