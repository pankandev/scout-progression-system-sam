from schema import SchemaError, Schema

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

    def _add_route_method(self, method: str, resource: str, fun, schema: Schema = None):
        if self.routes.get(method) is None:
            self.routes[method] = {}
        resource = self.standardize_resource(resource)
        self.routes[method][resource] = lambda evt: Router._validate_and_run(fun, evt, schema)

    @staticmethod
    def _validate_and_run(fun, evt: HTTPEvent, schema: Schema = None):
        if schema is not None:
            print(evt.json)
            schema.validate(evt.json)
        return fun(evt)

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
        except SchemaError as e:
            return JSONResponse.generate_error(HTTPError.INVALID_CONTENT, f"Bad schema: {e}")

    def post(self, resource: str, fun, schema: Schema = None):
        self._add_route_method("POST", resource, fun, schema=schema)

    def get(self, resource: str, fun, schema: Schema = None):
        self._add_route_method("GET", resource, fun, schema=schema)

    def delete(self, resource: str, fun, schema: Schema = None):
        self._add_route_method("DELETE", resource, fun, schema=schema)

    def patch(self, resource: str, fun, schema: Schema = None):
        self._add_route_method("PATCH", resource, fun, schema=schema)

    def put(self, resource: str, fun, schema: Schema = None):
        self._add_route_method("PUT", resource, fun, schema=schema)
