from abc import ABC


class CloudDAO(ABC):

    def __init__(self):
        self.init_connection()

    def upload_files(self):
        pass

    def download_files(self):
        pass

    def init_connection(self):
        pass
