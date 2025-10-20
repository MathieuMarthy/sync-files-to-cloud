from abc import ABC
from pathlib import Path


class CloudDAO(ABC):

    def upload_files(self, remote_folder: str, files: list[Path], local_base_path: Path = None):
        pass

    def download_files(self):
        pass

    def init_connection(self, can_open_connection_page: bool = False):
        """Establishes a connection to the cloud service and save credentials locally.

        Args:
            can_open_connection_page (bool): If True, the method can open the browser
                to complete the OAuth2 authentication flow. If False, it will raise an exception
                if no valid credentials are found.
        Raises:
            DaoConnectionException: If authentication is required but can_open_connection_page is False.
        """
        pass
