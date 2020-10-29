import json
import os

import boto3


class Bucket:

    @staticmethod
    def get_s3():
        return boto3.resource('s3')

    def __init__(self, bucket_name: str):
        self._bucket = self.get_s3().Bucket(bucket_name)
        self._jsons = dict()

    def download_json(self, path: str):
        data = self._jsons.get(path)
        if data is not None:
            return data

        download_path = os.path.join('/tmp', os.path.basename(path))
        self._bucket.download_file(path, download_path)
        with open(download_path, 'r') as f:
            data = json.load(f)
        return data
