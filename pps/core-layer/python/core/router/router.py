import traceback

from os import path
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

    def _add_route_method(self, method: str, resource: str, fun, schema: Schema = None, authorized=True):
        if self.routes.get(method) is None:
            self.routes[method] = {}
        resource = self.standardize_resource(resource)
        self.routes[method][resource] = lambda evt: Router._validate_and_run(fun, evt, schema=schema, authorized=True)
        if not authorized:
            public_resource = path.join(resource, 'public')
            self.routes[method][public_resource] = lambda evt: Router._validate_and_run(fun, evt, schema=schema,
                                                                                        authorized=False)

    @staticmethod
    def _validate_and_run(fun, evt: HTTPEvent, schema: Schema = None, authorized=True):
        if schema is not None:
            schema.validate(evt.json)
        if authorized and evt.authorizer is None:
            raise UnauthorizedException('You must be authenticated to access this resource')
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
        except Exception as e:
            body = {
                "code": HTTPError.SERVER_ERROR.name,
                "message": "An unknown error ocurred"
            }
            error = {
                "type": str(type(e)),
                "args": str(e.args),
                "traceback": [f.strip() for f in traceback.format_tb(e.__traceback__)]
            }
            if event.authorizer is not None and event.authorizer.is_admin:
                body["error"] = error
            return JSONResponse(body, 500)

    def post(self, resource: str, fun, schema: Schema = None, authorized=True):
        self._add_route_method("POST", resource, fun, schema=schema, authorized=authorized)

    def get(self, resource: str, fun, schema: Schema = None, authorized=True):
        self._add_route_method("GET", resource, fun, schema=schema, authorized=authorized)

    def delete(self, resource: str, fun, schema: Schema = None, authorized=True):
        self._add_route_method("DELETE", resource, fun, schema=schema, authorized=authorized)

    def patch(self, resource: str, fun, schema: Schema = None, authorized=True):
        self._add_route_method("PATCH", resource, fun, schema=schema, authorized=authorized)

    def put(self, resource: str, fun, schema: Schema = None, authorized=True):
        self._add_route_method("PUT", resource, fun, schema=schema, authorized=authorized)
