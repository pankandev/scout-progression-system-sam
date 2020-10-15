from enum import Enum
from typing import Dict


class HTTPError(Enum):
    NOT_FOUND = 0
    INVALID_ID = 1
    NOT_IMPLEMENTED = 2
    INVALID_CONTENT = 3
    UNKNOWN_ERROR = 4


ERROR_CODES: Dict[HTTPError, int] = {
    HTTPError.NOT_FOUND: 404,
    HTTPError.INVALID_ID: 400,
    HTTPError.NOT_IMPLEMENTED: 402,
    HTTPError.INVALID_CONTENT: 400,
    HTTPError.UNKNOWN_ERROR: 500
}
