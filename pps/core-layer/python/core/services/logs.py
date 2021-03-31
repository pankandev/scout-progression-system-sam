import time
from enum import Enum
from typing import Dict, Any, List

from core import ModelService
from core.exceptions.invalid import InvalidException


class LogTag(Enum):
    REWARD = 'REWARD',

    @staticmethod
    def from_value(value: str):
        for member in LogTag:
            if value == member.value:
                return member
        raise InvalidException(f"Unknown log tag: {value}")


class Log:
    tag: str
    timestamp: int
    log: str
    data: Dict[str, Any]

    def __init__(self, tag: LogTag, timestamp: int, log: str, data: Dict[str, Any] = None):
        self.tag = tag
        self.timestamp = timestamp
        self.log = log
        self.data = data

    @staticmethod
    def from_map(log_map: Dict[str, Any]):
        return Log(tag=log_map["tag"], timestamp=log_map["timestamp"], log=log_map["log"],
                   data=log_map["data"])

    def to_map(self):
        return {
            "tag": self.tag,
            "timestamp": self.timestamp,
            "log": self.log,
            "data": self.data
        }


class LogsService(ModelService):
    __table_name__ = "logs"
    __partition_key__ = "tag"
    __sort_key__ = "timestamp"

    @classmethod
    def query(cls, tag: str) -> List[Log]:
        return [Log.from_map(x) for x in cls.get_interface().query(tag).items]

    @classmethod
    def batch_create(cls, logs: List[Log]):
        count = 0
        for log in logs:
            log.timestamp = int(time.time() + count)
            count += 1
        cls.get_interface().client.batch_write_item(
            RequestItems={
                'logs': [
                    {
                        'PutRequest': {
                            'Item': {
                                'tag': {
                                    'S': log.tag.name if isinstance(log.tag, LogTag) else log.tag,
                                },
                                'timestamp': {
                                    'N': str(log.timestamp),
                                },
                                'log': {'S': log.log},
                                'data': {'M': log.data}
                            }
                        }
                    } for log in logs
                ]
            }
        )
