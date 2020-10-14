from typing import Dict


class CapacityUnits:
    def __init__(self, all_: float, read: float, write: float):
        self.all = all_
        self.read = read
        self.write = write

    @staticmethod
    def from_dict(d: Dict):
        return CapacityUnits(d['CapacityUnits'], d['ReadCapacityUnits'], d['WriteCapacityUnits'])


class ConsumedCapacity:
    def __init__(self,
                 table_name: str,
                 total: CapacityUnits,
                 table: CapacityUnits,
                 local_secondary_indexes: CapacityUnits,
                 global_secondary_indexes: CapacityUnits,
                 ):
        self.table_name = table_name
        self.total = total
        self.table = table
        self.local_secondary_indexes = local_secondary_indexes
        self.global_secondary_indexes = global_secondary_indexes

    @staticmethod
    def from_dict(d: Dict):
        if d is None:
            return None
        return ConsumedCapacity(
            table_name=d['TableName'],
            total=CapacityUnits.from_dict(d),
            table=CapacityUnits.from_dict(d.get('Table')),
            local_secondary_indexes=CapacityUnits.from_dict(d.get('LocalSecondaryIndexes')),
            global_secondary_indexes=CapacityUnits.from_dict(d.get('GlobalSecondaryIndexes'))
        )
