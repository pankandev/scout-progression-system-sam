import time
from datetime import datetime
from typing import Tuple, Union

SPLITTER = '::'


def clean_text(text: str, remove_spaces: bool = False, lower: bool = False):
    cleaned = ''.join([char for char in text if char.isalnum() or char == ' '])
    if remove_spaces:
        cleaned = cleaned.replace(' ', '-')
    if lower:
        cleaned = cleaned.lower()
    return cleaned


def join_key(*args):
    return SPLITTER.join(map(str, [arg for arg in args if arg is not None]))


def split_key(key: str):
    return key.split(SPLITTER)


def split_line(line: str) -> Tuple[int, Union[int, None]]:
    splitted = line.split('.')
    if len(splitted) == 2:
        try:
            return int(splitted[0]), int(splitted[1])
        except ValueError:
            return line, None
    return line, None


def epoch():
    return int(time.time())


def date_to_text(date: datetime) -> str:
    return date.strftime("%Y-%m-%d-%H-%M-%S")


def text_to_date(date: str) -> datetime:
    return datetime.strptime(date, "%Y-%m-%d-%H-%M-%S")


def generate_code(name: str, split=False):
    name = clean_text(name, remove_spaces=True).lower()
    s_date = date_to_text(datetime.now()).replace('-', '')
    if split:
        return join_key(name, s_date)
    return ''.join([name, s_date])
