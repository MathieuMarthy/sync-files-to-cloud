import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

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

    # Singleton pattern implementation
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GDriveCloudDAO, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()

    def _connect_to_gdrive(self):
        """Establishes a connection to Google Drive using OAuth2 credentials."""
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
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    utils.path(CREDENTIALS_PATH), SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for the next run
            with open(utils.path(TOKEN_PATH), "w") as token:
                token.write(creds.to_json())

        self.gdrive_service = build("drive", "v3", credentials=creds)

    def upload_files(self):
        raise NotImplemented()

    def download_files(self):
        raise NotImplemented()
