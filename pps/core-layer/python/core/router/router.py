from core import HTTPEvent, JSONResponse
from core.aws.errors import HTTPError
from core.exceptions.forbidden import ForbiddenException
from core.exceptions.invalid import InvalidException
from core.exceptions.notfound import NotFoundException
from core.exceptions.unauthorized import UnauthorizedException


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
        try:
            return fun(event)
        except ForbiddenException as e:
            return JSONResponse.generate_error(HTTPError.FORBIDDEN, e.message)
        except NotFoundException as e:
            return JSONResponse.generate_error(HTTPError.NOT_FOUND, e.message)
        except InvalidException as e:
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, e.message)
        except UnauthorizedException as e:
            return JSONResponse.generate_error(HTTPError.UNAUTHORIZED, e.message)

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
