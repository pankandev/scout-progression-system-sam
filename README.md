# Scout Personal Progression System SAM

[![Build Status](https://travis-ci.com/paths-ankan/scout-progression-system-sam.svg?token=KyjZA6my3g2pdNpkybPX&branch=master)](https://travis-ci.com/paths-ankan/scout-progression-system-sam)

This repository contains the code for a Scout Spirit Personal Progression System.

## Requirements

- AWS SAM
- Python 3.8
- Docker Compose

## Prepare testing environment

To test locally you need to run the database with Docker Compose:

````
docker-compose up
````

This will create the DynamoDB database. Now, to create the tables from the template.yaml you can use the script
in ``scripts/create_table.py``, which analyses the SAM template and create the tables in the local database:

``
pip install -r scripts/requirements.txt python scripts/create_table.py
``

Now to run the API Gateway, while the Docker is running, use another terminal and execute the following command:

````
sam build
sam local start-api --debug --env-vars environments/environment.dev.json --docker-network pps
````

This will run the API Gateway and all the Lambda Functions will be run on a Docker container connected to the ``pps``
Docker network to communicate with the database.

## Scripts

This repository contains some scripts to help with development

* ``create_table.py``: Create all the tables defined in the template.yaml.
* ``create_fake_data.py``: Create fake data (fixtures) in the database to test with
* ``reset_beneficiary.py -s <user-id>``: Reset a beneficiary data (this will not delete the beneficiary logs) on the
  database
* ``reset_logs.py``: Re-create the ``logs`` table on the database

## Fixtures

### Districts

````json
{
  "code": "pankan",
  "name": "Pankan District"
}
````

### Groups

Scouter Invitation URL:
http://localhost:4200/districts/pankan/groups/scout-spirit/invite?code=1a2b3c4d5e6f7g8h9i0j

````json
{
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
}
````

### Rewards

````json
[
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
````
