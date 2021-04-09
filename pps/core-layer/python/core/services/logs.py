import time
from enum import Enum
from typing import Dict, Any, List

from core import ModelService
from core.exceptions.invalid import InvalidException
from core.utils import join_key


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
        return Log(tag=log_map["tag"], timestamp=int(log_map["timestamp"]), log=log_map["log"],
                   data=log_map.get("data"))

    def to_map(self):
        data = {
            "tag": self.tag,
            "timestamp": self.timestamp,
            "log": self.log,
        }
        if self.data is not None:
            data['data'] = self.data
        return data

    def to_db_map(self):
        data = {
            'tag': self.tag.name if isinstance(self.tag, LogTag) else self.tag,
            'timestamp': self.timestamp,
            'log': self.log
        }
        if self.data is not None:
            data['data'] = self.data
        return data


class LogsService(ModelService):
    __table_name__ = "logs"
    __partition_key__ = "tag"
    __sort_key__ = "timestamp"

    @classmethod
    def query(cls, user_sub: str, tag: str, limit: int = 25) -> List[Log]:
        return cls.query_tag(join_key(user_sub, tag), limit=limit)

    @classmethod
    def query_tag(cls, tag: str, limit: int = None) -> List[Log]:
        return [Log.from_map(x) for x in cls.get_interface().query(tag, limit=limit, scan_forward=False).items]

    @staticmethod
    def _get_current_timestamp() -> int:
        return int(time.time() * 1000)

    @classmethod
    def batch_create(cls, logs: List[Log]):
        count = 0
        for log in logs:
            log.timestamp = cls._get_current_timestamp() + count
            count += 1
        items = [
            {
                'PutRequest': {
                    'Item': log.to_db_map()
                }
            } for log in logs
        ]
        cls.get_interface().client.batch_write_item(
            RequestItems={
                'logs': items
            }
        )

    @classmethod
    def create(cls, sub: str, tag: str, log_text: str, data: Any) -> Log:
        log = Log(tag=join_key(sub, tag.upper()), log=log_text, data=data, timestamp=cls._get_current_timestamp())
        cls.get_interface().create(log.tag, log.to_db_map(), log.timestamp)
        return log

    @classmethod
    def get_last_log_with_tag(cls, sub: str, tag: str) -> Log:
        logs = cls.get_interface().query(join_key(sub, tag.upper()), limit=1, scan_forward=False).items
        if len(logs) > 0:
            return Log.from_map(logs[0])
        return None
