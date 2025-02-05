from enum import Enum
from typing import Dict


class HTTPError(Enum):
    NOT_FOUND = 0
    INVALID_ID = 1
    NOT_IMPLEMENTED = 2
    INVALID_CONTENT = 3
    UNKNOWN_ERROR = 4
    UNKNOWN_RESOURCE = 5
    FORBIDDEN = 6
    EMAIL_ALREADY_IN_USE = 7
    UNCONFIRMED_USER = 8
    UNKNOWN_USER = 9
    ALREADY_IN_USE = 10
    UNAUTHORIZED = 11
    SERVER_ERROR = 12


ERROR_CODES: Dict[HTTPError, int] = {
    HTTPError.NOT_FOUND: 404,
    HTTPError.INVALID_ID: 400,
    HTTPError.NOT_IMPLEMENTED: 402,
    HTTPError.INVALID_CONTENT: 400,
    HTTPError.UNKNOWN_ERROR: 500,
    HTTPError.UNKNOWN_RESOURCE: 500,
    HTTPError.FORBIDDEN: 403,
    HTTPError.EMAIL_ALREADY_IN_USE: 400,
    HTTPError.UNCONFIRMED_USER: 403,
    HTTPError.UNKNOWN_USER: 404,
    HTTPError.ALREADY_IN_USE: 400,
    HTTPError.UNAUTHORIZED: 401,
    HTTPError.SERVER_ERROR: 500
}
