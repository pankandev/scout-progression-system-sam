import json
import os

import boto3

from core.aws.event import Authorizer


class Bucket:

    @staticmethod
    def get_s3():
        return boto3.resource('s3')

    def __init__(self, bucket_name: str):
        self._bucket = self.get_s3().Bucket(bucket_name)
        self._jsons = dict()

    def download_json(self, key: str):
        data = self._jsons.get(key)
        if data is not None:
            return data

        download_path = f"/tmp/{key}"
        self._bucket.download_file(Key=key, Filename=download_path)
        with open(download_path, 'r') as f:
            data = json.load(f)
        return data

    def save_json(self, item: dict, key: str):
        self._bucket.put_object(Body=json.dumps(item, ensure_ascii=False).encode('utf-8'), Key=key)
