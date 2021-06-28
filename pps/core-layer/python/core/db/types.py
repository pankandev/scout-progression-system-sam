from typing import TypeVar, Set, List, Dict

DynamoDBTypes = TypeVar('DynamoDBTypes',
                        str,
                        bytes,
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
