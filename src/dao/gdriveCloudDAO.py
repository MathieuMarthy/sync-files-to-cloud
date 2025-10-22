import logging
import os.path
from pathlib import Path

import googleapiclient
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from httplib2 import ServerNotFoundError

from src import utils
from src.dao.cloudDAO import CloudDAO
from src.exceptions.DaoException import DaoConnectionException, AuthentificationRequiredException, \
    NoCredentialFileException, NoInternet

# define the scopes for Google Drive API
# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Define paths for token and credentials
TOKEN_PATH = "credentials/token.json"
CREDENTIALS_PATH = "credentials/gdrive_credentials.json"


class GDriveCloudDAO(CloudDAO):
    _instance = None
    gdrive_service: Resource

    def __init__(self):
        super().__init__()
        self._folder_cache = {}  # Cache for folder IDs: {folder_path: folder_id}

    def upload_files(self, remote_folder: str, files: list[Path], local_base_path: Path = None):
        # Clear cache at the beginning of each upload session
        self._folder_cache.clear()

        # Get or create the folder ID from the remote_path
        try:
            folder_id = self._get_or_create_folder(remote_folder)

            for file in files:
                target_folder_id = self._determine_target_folder(file, remote_folder, folder_id, local_base_path)
                self._upload_single_file(file, target_folder_id)
        except ServerNotFoundError:
            raise NoInternet("Don't have access to internet or the cloud provider api is down")


    def _determine_target_folder(self, file: Path, remote_folder: str, default_folder_id: str,
                                 local_base_path: Path = None) -> str:
        """Determine the target folder ID for a file based on its local path structure."""
        if local_base_path and file.is_relative_to(local_base_path):
            relative_path = file.relative_to(local_base_path)
            if relative_path.parent != Path("."):
                # File is in a subdirectory, create the full path
                target_folder_path = f"{remote_folder.rstrip('/')}/{relative_path.parent.as_posix()}"
                return self._get_or_create_folder(target_folder_path)

        return default_folder_id

    def _upload_single_file(self, file: Path, target_folder_id: str):
        """Upload or update a single file to Google Drive."""
        name = os.path.basename(str(file))
        q_name = name.replace("'", "\\'")  # Escape single quotes for the Drive query

        # Check if file exists and needs update
        existing_file_id = self._find_existing_file(q_name, target_folder_id)

        if existing_file_id:
            self._update_file_if_changed(file, name, existing_file_id)
        else:
            self._create_new_file(file, name, target_folder_id)

    def _find_existing_file(self, q_name: str, target_folder_id: str) -> str | None:
        """Search for an existing file in the target folder. Returns file ID if found, None otherwise."""
        query = f"name = '{q_name}' and '{target_folder_id}' in parents and trashed = false"
        results = self.gdrive_service.files().list(
            q=query,
            spaces="drive",
            fields="files(id, name, md5Checksum)"
        ).execute()

        items = results.get("files", [])
        return items[0]["id"] if items else None

    def _update_file_if_changed(self, file: Path, name: str, existing_file_id: str):
        """Update a file only if its content has changed (based on MD5 hash)."""
        local_md5 = utils.calculate_md5(file)

        # Get remote file metadata
        remote_file = self.gdrive_service.files().get(
            fileId=existing_file_id,
            fields="md5Checksum"
        ).execute()

        remote_md5 = remote_file.get("md5Checksum")

        if remote_md5 == local_md5:
            logging.debug(f"File '{name}' is already up to date, skipping upload")
        else:
            media = googleapiclient.http.MediaFileUpload(str(file), resumable=True)
            updated_file = self.gdrive_service.files().update(
                fileId=existing_file_id,
                media_body=media,
                fields="id"
            ).execute()
            logging.debug(f"File '{name}' has been updated with ID: {updated_file['id']}")

    def _create_new_file(self, file: Path, name: str, target_folder_id: str):
        """Create a new file in Google Drive."""
        media = googleapiclient.http.MediaFileUpload(str(file), resumable=True)
        file_metadata = {
            "name": name,
            "parents": [target_folder_id]
        }
        uploaded_file = self.gdrive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        logging.debug(f"File '{name}' uploaded with ID: {uploaded_file['id']}")

    def _get_or_create_folder(self, folder_path: str) -> str:
        """
        Get or create a folder in Google Drive from a path like "/images" or "/backup/photos".
        Returns the folder ID. Uses cache to avoid repeated lookups.
        """
        # Check cache first
        if folder_path in self._folder_cache:
            return self._folder_cache[folder_path]

        # Remove leading/trailing slashes and split the path
        folder_path_normalized = folder_path.strip("/")

        if not folder_path_normalized:
            # If empty path, return root folder ("root")
            self._folder_cache[folder_path] = "root"
            return "root"

        folder_names = folder_path_normalized.split("/")
        parent_id = "root"

        # Navigate/create each folder in the path
        for i, folder_name in enumerate(folder_names):
            # Build the path up to this point for caching
            current_path = "/" + "/".join(folder_names[:i + 1])

            # Check if this intermediate path is already cached
            if current_path in self._folder_cache:
                parent_id = self._folder_cache[current_path]
                continue

            # Search for the folder
            query = f"name='{folder_name}' and '{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
            results = self.gdrive_service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name)"
            ).execute()

            items = results.get("files", [])

            if items:
                # Folder exists, use its ID
                parent_id = items[0]["id"]
                logging.debug(f"Found existing folder '{folder_name}' with ID: {parent_id}")
            else:
                # Folder doesn't exist, create it
                folder_metadata = {
                    "name": folder_name,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [parent_id]
                }
                folder = self.gdrive_service.files().create(
                    body=folder_metadata,
                    fields="id"
                ).execute()
                parent_id = folder["id"]
                logging.debug(f"Created folder '{folder_name}' with ID: {parent_id}")

            # Cache this path
            self._folder_cache[current_path] = parent_id

        # Cache the final full path
        self._folder_cache[folder_path] = parent_id
        return parent_id

    def download_files(self):
        raise NotImplemented()

    def init_connection(self, can_open_connection_page: bool = False):
        # code adapted from https://developers.google.com/workspace/drive/api/quickstart/python

        creds = None

        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(utils.path(TOKEN_PATH)):
            creds = Credentials.from_authorized_user_file(utils.path(TOKEN_PATH), SCOPES)

        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logging.debug("GDrive: token expired, refreshing the token")
                creds.refresh(Request())
            elif can_open_connection_page:
                logging.debug("GDrive: no valid token found, starting the login flow")

                if not os.path.exists(utils.path(CREDENTIALS_PATH)):
                    raise NoCredentialFileException("GDrive: missing credentials file for authentication. Please provide the file at {CREDENTIALS_PATH}")

                flow = InstalledAppFlow.from_client_secrets_file(
                    utils.path(CREDENTIALS_PATH), SCOPES
                )
                creds = flow.run_local_server(port=0)
            else:
                if not os.path.exists(utils.path(CREDENTIALS_PATH)):
                    raise NoCredentialFileException(f"GDrive: missing credentials file for authentication. Please provide the file at {CREDENTIALS_PATH}")

                raise AuthentificationRequiredException("GDrive: need to authenticate in the browser")

                # Save the credentials for the next run
            with open(utils.path(TOKEN_PATH), "w") as token:
                token.write(creds.to_json())

        self.gdrive_service = build("drive", "v3", credentials=creds)
        logging.debug("GDrive: connection established")
