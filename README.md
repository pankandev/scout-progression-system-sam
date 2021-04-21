# Scout Personal Progression System SAM 

[![Build Status](https://travis-ci.com/paths-ankan/scout-progression-system-sam.svg?token=KyjZA6my3g2pdNpkybPX&branch=master)](https://travis-ci.com/paths-ankan/scout-progression-system-sam)

This repository contains the code for a Scout Spirit Personal Progression System.

## Requirements

- AWS SAM
- Python 3.8
- Docker Compose

## Prepare testing environment

To test locally you need to run the database with Docker Compose:

````sh
docker-compose up
````

This will create the DynamoDB database. Now, to create the tables from the template.yaml
you can use the script in ``scripts/create_table.py``, which analyses the SAM template
and create the tables in the local database:

``
pip install -r scripts/requirements.txt
python scripts/create_table.py
``

Now to run the API Gateway, while the Docker is running, use another terminal
and execute the following command:

````sh
sam build
sam local start-api --debug --env-vars environments/environment.dev.json --docker-network pps
````

This will run the API Gateway and all the Lambda Functions will be run through the ``pps``
Docker network to communicate with the database.

## Scripts

This repository contains some scripts to help with development

* ``create_table.py``: Create all the tables defined in the template.yaml.
* ``create_fake_data.py``: Create fake data in the database to test with
* ``reset_beneficiary.py -s <user-id>``: Reset a beneficiary data (this will not delete
the beneficiary logs) on the database
* ``reset_logs.py``: Re-create the ``logs`` table on the database
