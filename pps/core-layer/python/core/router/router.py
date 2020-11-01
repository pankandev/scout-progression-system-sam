from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError


class Router:
    def __init__(self):
        self.routes = {}

    @staticmethod
    def standardize_resource(resource: str):
        return '/'.join(filter(lambda x: x != '', resource.split('/')))

    def _add_route_method(self, method: str, resource: str, fun):
        if self.routes.get(method) is None:
            self.routes[method] = {}
        resource = self.standardize_resource(resource)
        self.routes[method][resource] = fun

    def route(self, event: HTTPEvent) -> JSONResponse:
        resources = self.routes.get(event.method)
        if resources is None:
            return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown method {event.method}")
        resource = self.standardize_resource(event.resource)
        fun = resources.get(resource)
        if fun is None:
            return JSONResponse.generate_error(HTTPError.UNKNOWN_RESOURCE, f"Unknown resource {event.resource}")
        return fun(event)

    def post(self, resource: str, fun):
        self._add_route_method("POST", resource, fun)

    def get(self, resource: str, fun):
        self._add_route_method("GET", resource, fun)

    def delete(self, resource: str, fun):
        self._add_route_method("DELETE", resource, fun)

    def patch(self, resource: str, fun):
        self._add_route_method("PATCH", resource, fun)

    def put(self, resource: str, fun):
        self._add_route_method("PUT", resource, fun)
