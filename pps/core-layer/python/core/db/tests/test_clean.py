from decimal import Decimal

from core.db.results import clean_item


def test_clean():
    cleaned = clean_item({
        'a': Decimal(0),
        'b': 'abc',
        'c': {
            'd': Decimal(1),
            'e': 'def'
        }
    })

    assert type(cleaned['a']) is float
    assert type(cleaned['c']['d']) is float

    assert cleaned == {
        'a': 0,
        'b': 'abc',
        'c': {
            'd': 1,
            'e': 'def'
        }
    }
