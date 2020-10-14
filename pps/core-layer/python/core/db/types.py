from typing import TypeVar, AnyStr, Set, List, Dict

DynamoDBTypes = TypeVar('DynamoDBTypes',
                        AnyStr,
                        int,
                        float,
                        bool,
                        type(None),
                        Set[str],
                        Set[int],
                        Set[bytes],
                        List,
                        Dict)
DynamoDBKey = Dict[str, DynamoDBTypes]
