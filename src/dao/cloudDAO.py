from abc import ABC


class CloudDAO(ABC):

    def __init__(self):
        self._connect()

    def upload_files(self):
        pass

    def download_files(self):
        pass

    def _connect(self):
        pass

    @staticmethod
    def init_connection():
        pass
