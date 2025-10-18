import logging
import os.path
from pathlib import Path

import googleapiclient
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from src import utils
from src.dao.cloudDAO import CloudDAO

# define the scopes for Google Drive API
# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

# Define paths for token and credentials
TOKEN_PATH = "credentials/token.json"
CREDENTIALS_PATH = "credentials/gdrive_credentials.json"


class GDriveCloudDAO(CloudDAO):
    _instance = None
    gdrive_service: Resource

    def upload_files(self, remote_folder: str, files: list[Path], local_base_path: Path = None):
        # Get or create the folder ID from the remote_path
        folder_id = self._get_or_create_folder(remote_folder)

        for file in files:
            # Determine the target folder for this file
            if local_base_path and file.is_relative_to(local_base_path):
                # Calculate relative path from base path
                relative_path = file.relative_to(local_base_path)
                # Get the parent directory of the file (if any)
                if relative_path.parent != Path("."):
                    # File is in a subdirectory, create the full path
                    target_folder_path = f"{remote_folder.rstrip('/')}/{relative_path.parent.as_posix()}"
                    target_folder_id = self._get_or_create_folder(target_folder_path)
                else:
                    # File is at the root of local_base_path
                    target_folder_id = folder_id
            else:
                # No base path provided, use root folder
                target_folder_id = folder_id

            name = os.path.basename(str(file))
            # Escape single quotes for the Drive query
            q_name = name.replace("'", "\\'")

            # Calculate MD5 hash of the local file
            local_md5 = utils.calculate_md5(file)

            # Search for an existing file with the same name in the target folder (not trashed)
            query = f"name = '{q_name}' and '{target_folder_id}' in parents and trashed = false"
            results = self.gdrive_service.files().list(
                q=query,
                spaces="drive",
                fields="files(id, name, md5Checksum)"
            ).execute()

            items = results.get("files", [])

            if items:
                # File exists, check if content has changed
                existing_id = items[0]["id"]
                remote_md5 = items[0].get("md5Checksum")

                if remote_md5 == local_md5:
                    # File hasn't changed, skip upload
                    logging.info(f"File '{name}' is already up to date, skipping upload")
                    continue
                else:
                    # File has changed, update it
                    media = googleapiclient.http.MediaFileUpload(str(file), resumable=True)
                    updated_file = self.gdrive_service.files().update(
                        fileId=existing_id,
                        media_body=media,
                        fields="id"
                    ).execute()
                    logging.info(f"File '{name}' has been updated with ID: {updated_file['id']}")
            else:
                # Create new file in the target folder
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
                logging.info(f"File '{name}' uploaded with ID: {uploaded_file['id']}")

    def _get_or_create_folder(self, folder_path: str) -> str:
        """
        Get or create a folder in Google Drive from a path like "/images" or "/backup/photos".
        Returns the folder ID.
        """
        # Remove leading/trailing slashes and split the path
        folder_path = folder_path.strip("/")

        if not folder_path:
            # If empty path, return root folder ("root")
            return "root"

        folder_names = folder_path.split("/")
        parent_id = "root"

        # Navigate/create each folder in the path
        for folder_name in folder_names:
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
                logging.info(f"Found existing folder '{folder_name}' with ID: {parent_id}")
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
                logging.info(f"Created folder '{folder_name}' with ID: {parent_id}")

        return parent_id

    def download_files(self):
        raise NotImplemented()

    def init_connection(self):
        """Establishes a connection to Google Drive API and save the credentials in a file."""
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
                logging.info("GDrive: token expired, refreshing the token")
                creds.refresh(Request())
            else:
                logging.info("GDrive: no valid token found, starting the login flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    utils.path(CREDENTIALS_PATH), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(utils.path(TOKEN_PATH), "w") as token:
                token.write(creds.to_json())

        self.gdrive_service = build("drive", "v3", credentials=creds)
        logging.info("GDrive: connection established")
