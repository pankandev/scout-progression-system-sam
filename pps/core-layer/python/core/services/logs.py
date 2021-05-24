from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Union

from core import ModelService
from core.db.model import Operator, BoolOperator
from core.exceptions.invalid import InvalidException
from core.utils import join_key
from core.utils.key import SPLITTER, split_key


class LogTag(Enum):
    REWARD = 'REWARD',
    PROGRESS = 'PROGRESS'
    COMPLETE = 'COMPLETE'

    @staticmethod
    def concat(parent_tag: str, *args):
        return join_key(parent_tag, *args)

    @staticmethod
    def from_value(value: str):
        for member in LogTag:
            if value == member.value:
                return member
        raise InvalidException(f"Unknown log tag: {value}")


class LogKey:
    sub: str
    tag: str

    def __init__(self, sub: str, tag: str):
        self.sub = sub
        self.tag = tag


class Log:
    sub: str
    tag: List[str]
    timestamp: Union[int, None]
    log: str
    data: Dict[str, Any]

    append_timestamp = False

    def __init__(self, sub: str, tag: LogTag, log: str, timestamp: int = None, data: Dict[str, Any] = None,
                 append_timestamp: bool = False):
        self.sub = sub
        self.tag = tag
        self.timestamp = int(timestamp) if timestamp is not None else None
        self.log = log
        self.data = data
        self.append_timestamp = append_timestamp

    @property
    def parent_tag(self) -> LogTag:
        return LogTag.from_value(self.tags[0])

    @property
    def tags(self) -> List[str]:
        return split_key(self.tag)

    @staticmethod
    def from_map(log_map: Dict[str, Any], append_timestamp: bool = False):
        tag = log_map.get("tag")
        return Log(sub=log_map.get("user"), tag=tag, timestamp=log_map.get("timestamp"), log=log_map.get("log"),
                   data=log_map.get("data"), append_timestamp=append_timestamp)

    def to_map(self):
        tag = self.tag.name if isinstance(self.tag, LogTag) else self.tag
        data = {
            "tag": tag if not self.append_timestamp else join_key(tag, self.timestamp),
            "user": self.sub,
            "log": self.log,
            'timestamp': self.timestamp
        }
        if self.data is not None:
            data['data'] = self.data
        return data

    def to_db_map(self):
        tag = self.tag.name if isinstance(self.tag, LogTag) else self.tag
        data = {
            "tag": tag if not self.append_timestamp else join_key(tag, self.timestamp),
            'user': self.sub,
            'log': self.log,
            'timestamp': self.timestamp
        }

        if self.data is not None:
            data['data'] = self.data
        return data


class LogsService(ModelService):
    __table_name__ = "logs"
    __partition_key__ = "user"
    __sort_key__ = "tag"
    __indices__ = {
        "ByTimestamp": ("user", "timestamp")
    }

    @classmethod
    def query(cls, user_sub: str, tag: str = None, limit: int = 25) -> List[Log]:
        return cls.query_tag(user_sub, tag, limit=limit)

    @classmethod
    def query_tag(cls, user: str, tag: str = None, limit: int = None, is_full=True) -> List[Log]:
        return [Log.from_map(x) for x in cls.get_interface().query(user, sort_key=(
            Operator.BEGINS_WITH, tag + (SPLITTER if not is_full else '')) if tag is not None else None,
                                                                   limit=limit, scan_forward=False).items]

    @classmethod
    def query_tags(cls, user: str, tags: List[str], limit: int = None, is_full=True) -> List[Log]:
        return [Log.from_map(x) for x in cls.get_interface().query(
            user,
            sort_key=[(Operator.BEGINS_WITH, tag + (SPLITTER if not is_full else '')) for tag in tags],
            limit=limit,
            scan_forward=False,
            bool_op=BoolOperator.OR
        ).items]

    @staticmethod
    def _get_current_timestamp() -> int:
        now = datetime.now(timezone.utc)
        return int(now.timestamp() * 1000)

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
    def create(cls, sub: str, tag: str, log_text: str, data: Any, append_timestamp_to_tag: bool = False) -> Log:
        log = Log(tag=tag.upper(), log=log_text, data=data, timestamp=cls._get_current_timestamp(), sub=sub,
                  append_timestamp=append_timestamp_to_tag)
        cls.get_interface().create(sub,
                                   log.to_db_map(),
                                   join_key(log.tag, log.timestamp) if log.append_timestamp else log.tag)
        return log

    @classmethod
    def get_last_log_with_tag(cls, sub: str, tag: str, is_full=False) -> Log:
        logs = cls.get_interface().query(sub, (Operator.BEGINS_WITH, tag + (SPLITTER if not is_full else '')), limit=1,
                                         scan_forward=False).items
        if len(logs) > 0:
            return Log.from_map(logs[0])
        return None

    @classmethod
    def batch_get(cls, keys: List[LogKey], attributes: List[str] = None) -> List[Log]:
        items = {
            'Keys': [{
                'tag': key.tag,
                'user': key.sub,
            } for key in keys],
        }
        if attributes is not None:
            items['AttributesToGet'] = attributes

        response = cls.get_interface().client.batch_get_item(
            RequestItems={
                'logs': items
            }
        )
        logs: List[dict] = response['Responses']['logs']
        return [Log.from_map(x) for x in logs]
