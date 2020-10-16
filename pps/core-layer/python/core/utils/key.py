from datetime import datetime

SPLITTER = '::'


def clean_text(text: str):
    return ''.join([char for char in text if char.isalnum() or char == ' '])


def join_key(*args):
    return SPLITTER.join(args)


def split_key(key: str):
    return key.split(SPLITTER)


def date_to_text(date: datetime) -> str:
    return date.strftime("%d-%m-%Y")


def text_to_date(date: str) -> datetime:
    return datetime.strptime(date, "%d-%m-%Y")


def generate_code(name: str):
    name = clean_text(name).lower()
    s_date = date_to_text(datetime.now()).replace('-', '')
    return join_key(name, s_date)
