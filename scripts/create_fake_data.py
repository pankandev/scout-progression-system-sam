import os

import boto3

dir_path = os.path.dirname(os.path.realpath(__file__))

rewards = [
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "^"
            },
            "type": "eye"
        },
        "rarity": "RARE",
        "release-id": -91932
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "w"
            },
            "type": "mouth"
        },
        "rarity": "RARE",
        "release-id": -80561
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "purple"
            },
            "type": "neckerchief"
        },
        "rarity": "RARE",
        "release-id": -70842
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "pink"
            },
            "type": "neckerchief"
        },
        "rarity": "RARE",
        "release-id": -68075
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "red",
                "type": "common"
            },
            "type": "shirt"
        },
        "rarity": "COMMON",
        "release-id": 2415
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "blue",
                "type": "common"
            },
            "type": "shirt"
        },
        "rarity": "COMMON",
        "release-id": 5775
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "green",
                "type": "common"
            },
            "type": "shirt"
        },
        "rarity": "COMMON",
        "release-id": 8851
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "red"
            },
            "type": "pants"
        },
        "rarity": "COMMON",
        "release-id": 46384
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "blue"
            },
            "type": "pants"
        },
        "rarity": "COMMON",
        "release-id": 50246
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "green"
            },
            "type": "pants"
        },
        "rarity": "COMMON",
        "release-id": 53559
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "red",
                "type": "common"
            },
            "type": "shirt"
        },
        "rarity": "COMMON",
        "release-id": 53678
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "red"
            },
            "type": "neckerchief"
        },
        "rarity": "COMMON",
        "release-id": 59639
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "blue"
            },
            "type": "neckerchief"
        },
        "rarity": "COMMON",
        "release-id": 62180
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "green"
            },
            "type": "neckerchief"
        },
        "rarity": "COMMON",
        "release-id": 64437
    },
    {
        "category": "AVATAR",
        "description": {
            "description": {
                "material": "shirt",
                "type": "common"
            },
            "type": "shirt"
        },
        "rarity": "COMMON",
        "release-id": 86746
    },
    {
        "category": "DECORATION",
        "description": {
            "code": "rare-block",
            "type": "block"
        },
        "rarity": "RARE",
        "release-id": -82676
    },
    {
        "category": "DECORATION",
        "description": {
            "code": "rare-path",
            "type": "path"
        },
        "rarity": "RARE",
        "release-id": -77944
    },
    {
        "category": "DECORATION",
        "description": {
            "code": "wood-path",
            "type": "path"
        },
        "rarity": "COMMON",
        "release-id": 63714
    },
    {
        "category": "DECORATION",
        "description": {
            "code": "wood-block",
            "type": "block"
        },
        "rarity": "COMMON",
        "release-id": 71792
    },
    {
        "category": "ZONE",
        "description": {
            "code": "zone-d"
        },
        "rarity": "RARE",
        "release-id": -48325
    },
    {
        "category": "ZONE",
        "description": {
            "code": "zone-c"
        },
        "rarity": "RARE",
        "release-id": -46445
    },
    {
        "category": "ZONE",
        "description": {
            "code": "zone-a"
        },
        "rarity": "COMMON",
        "release-id": 39353
    },
    {
        "category": "ZONE",
        "description": {
            "code": "zone-b"
        },
        "rarity": "COMMON",
        "release-id": 42905
    }
]

if __name__ == "__main__":
    db_client = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
    group_table = db_client.Table("groups")
    districts_table = db_client.Table("districts")
    rewards_table = db_client.Table("rewards")

    districts_table.put_item(
        Item={
            "code": "pankan"
        })
    group_table.put_item(
        Item={
            "beneficiary_code": "123456789",
            "code": "scout-spirit",
            "creator": "80bae819-88c5-4e66-9918-3b6b98acf0ce",
            "district": "pankan",
            "name": "Scout Spirit Group",
            "scouters": {
                "scouter-sub": {
                    "name": "Group Scouter",
                    "role": "creator"
                }
            },
            "scouters_code": "1a2b3c4d5e6f7g8h9i0j"
        })
    for reward in rewards:
        rewards_table.put_item(
            Item=reward
        )
