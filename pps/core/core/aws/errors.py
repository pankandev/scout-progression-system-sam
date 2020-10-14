from enum import Enum
from typing import Dict


class HTTPError(Enum):
    NOT_FOUND = 0
    INVALID_ID = 1


ERROR_CODES: Dict[HTTPError, int] = {
    HTTPError.NOT_FOUND: 404,
    HTTPError.INVALID_ID: 400
}
