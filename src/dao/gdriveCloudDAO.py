import logging
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build, Resource

from src import utils
from src.dao.cloudDAO import CloudDAO
from src.exceptions.DaoException import DaoConnectionException

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

    def upload_files(self):
        raise NotImplemented()

    def download_files(self):
        raise NotImplemented()

    def _connect(self):
        if os.path.exists(utils.path(TOKEN_PATH)):
            logging.info("GDrive: connection using the token file")
            creds = Credentials.from_authorized_user_file(utils.path(TOKEN_PATH), SCOPES)

            # check if the token is valid
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    logging.info("GDrive: token expired, refreshing the token")
                    creds.refresh(Request())
                else:  # the user need to reconnect
                    raise DaoConnectionException(
                        "GDrive: credentials are not valid, please restart the script and reconnect to GDrive"
                    )

            self.gdrive_service = build("drive", "v3", credentials=creds)
            logging.info("GDrive: connection established")
        else:
            raise DaoConnectionException(f"GDrive: not found the token file, token file: {TOKEN_PATH}")

    @staticmethod
    def init_connection():
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
