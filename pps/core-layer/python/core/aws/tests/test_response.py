from decimal import Decimal

from .. import JSONResponse


def test_clean():
    cleaned = JSONResponse.clean_for_json({
        'a': Decimal('12.0'),
        'b': Decimal('12.3'),
        'c': 'qwerty',
        'd': {
            'c.a': Decimal('123'),
            'c.b': 'asdf'
        }
    })
    assert cleaned['a'] == 12 and type(cleaned['a']) is int
    assert cleaned['b'] == 12.3 and type(cleaned['b']) is float
    assert cleaned['c'] == 'qwerty'
    assert cleaned['d'] == {
        'c.a': 123,
        'c.b': 'asdf'
    }
