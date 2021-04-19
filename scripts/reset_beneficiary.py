from argparse import ArgumentParser

import boto3

updates = {
    "avatar": {
        "bottom": None,
        "left_eye": None,
        "mouth": None,
        "neckerchief": None,
        "right_eye": None,
        "top": None
    },
    "birthdate": "17-04-2001",
    "bought_items": {},
    "generated_token_last": 0,
    "n_claimed_tokens": 0,
    "n_tasks": {
        "affectivity": 0,
        "character": 0,
        "corporality": 0,
        "creativity": 0,
        "sociability": 0,
        "spirituality": 0
    },
    "score": {
        "affectivity": 0,
        "character": 0,
        "corporality": 0,
        "creativity": 0,
        "sociability": 0,
        "spirituality": 0
    },
    "set_base_tasks": False,
    "target": None,
}

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('--sub', '-s', help='User sub of the beneficiary to reset', required=True)
    args = parser.parse_args()
    sub = args.sub

    db_client = boto3.resource('dynamodb', endpoint_url="http://localhost:8000")
    beneficiaries_table = db_client.Table("beneficiaries")

    beneficiaries_table.update_item(
        Key={'user': sub},
        UpdateExpression="SET " + ','.join([
            f"#attr_{key}=:val_{key}" for key in updates.keys()
        ]),
        ExpressionAttributeNames={f"#attr_{key}": key for key in updates.keys()},
        ExpressionAttributeValues={f":val_{key}": value for key, value in updates.items()},
    )
