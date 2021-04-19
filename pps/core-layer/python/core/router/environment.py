import os

__all__ = ['ENVIRONMENT']

BOOL_NAMES = {
    'true': True,
    'false': False
}


class AppEnvironment:
    @property
    def stage(self):
        return os.environ.get('STAGE', 'PROD')

    @property
    def is_production(self):
        return self.stage == 'PROD'

    @property
    def is_local(self):
        return BOOL_NAMES[os.environ.get('AWS_SAM_LOCAL', 'false')]

    @property
    def aws_region(self):
        return os.environ.get('AWS_REGION', 'us-west-2')


ENVIRONMENT = AppEnvironment()
