from abc import ABC
from pathlib import Path


class CloudDAO(ABC):

    def upload_files(self, remote_folder: str, files: list[Path]):
        pass

    def download_files(self):
        pass

    def init_connection(self):
        pass
