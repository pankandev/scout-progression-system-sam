from abc import ABC


class AppException(Exception, ABC):
    message: dict

    def __init__(self, message: dict):
        self.message = message
