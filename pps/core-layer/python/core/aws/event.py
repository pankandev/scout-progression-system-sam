import os


class HTTPEvent:
    def __init__(self, event: dict):
        self.body = event.get("body")
        self.resource: str = event.get("resource")
        self.method: str = event.get("httpMethod")
        self.headers: dict = event.get("headers")
        self.context: dict = event.get("requestContext")

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
