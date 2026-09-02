import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest
from httplib2 import ServerNotFoundError

from src.dao.gdriveCloudDAO import GDriveCloudDAO
from src.exceptions.DaoException import (
    AuthentificationRequiredException,
    NoCredentialFileException,
    NoInternet,
)


@pytest.fixture
def gdrive_dao():
    dao = GDriveCloudDAO()
    dao.gdrive_service = MagicMock()
    return dao


def test_init_connection_valid_token(gdrive_dao):
    mock_creds = MagicMock()
    mock_creds.valid = True

    with patch("os.path.exists", return_value=True), patch(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        return_value=mock_creds,
    ), patch("src.dao.gdriveCloudDAO.build") as mock_build:
        gdrive_dao.init_connection()
        mock_build.assert_called_once_with("drive", "v3", credentials=mock_creds)


def test_init_connection_expired_token_refreshes(gdrive_dao):
    mock_creds = MagicMock()
    mock_creds.valid = False
    mock_creds.expired = True
    mock_creds.refresh_token = "refresh_token_123"
    mock_creds.to_json.return_value = "{}"

    with patch("os.path.exists", return_value=True), patch(
        "google.oauth2.credentials.Credentials.from_authorized_user_file",
        return_value=mock_creds,
    ), patch("google.auth.transport.requests.Request"), patch(
        "builtins.open", mock_open()
    ), patch(
        "src.dao.gdriveCloudDAO.build"
    ):
        gdrive_dao.init_connection()
        mock_creds.refresh.assert_called_once()


def test_init_connection_no_token_missing_credentials_file(gdrive_dao):
    with patch("os.path.exists", return_value=False):
        with pytest.raises(NoCredentialFileException):
            gdrive_dao.init_connection(can_open_connection_page=False)


def test_init_connection_no_token_auth_required_exception(gdrive_dao):
    def mock_exists(p):
        if "token.json" in str(p):
            return False
        if "gdrive_credentials.json" in str(p):
            return True
        return False

    with patch("os.path.exists", side_effect=mock_exists):
        with pytest.raises(AuthentificationRequiredException):
            gdrive_dao.init_connection(can_open_connection_page=False)


def test_init_connection_open_connection_page_runs_flow(gdrive_dao):
    def mock_exists(p):
        if "token.json" in str(p):
            return False
        if "gdrive_credentials.json" in str(p):
            return True
        return False

    mock_creds = MagicMock()
    mock_creds.valid = True
    mock_creds.to_json.return_value = "{}"

    mock_flow = MagicMock()
    mock_flow.run_local_server.return_value = mock_creds

    with patch("os.path.exists", side_effect=mock_exists), patch(
        "google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file",
        return_value=mock_flow,
    ), patch("builtins.open", mock_open()), patch(
        "src.dao.gdriveCloudDAO.build"
    ):
        gdrive_dao.init_connection(can_open_connection_page=True)
        mock_flow.run_local_server.assert_called_once_with(port=0)




def test_get_or_create_folder_root(gdrive_dao):
    assert gdrive_dao._get_or_create_folder("/") == "root"
    assert gdrive_dao._get_or_create_folder("") == "root"


def test_get_or_create_folder_cached(gdrive_dao):
    gdrive_dao._folder_cache["/photos"] = "folder_123"
    assert gdrive_dao._get_or_create_folder("/photos") == "folder_123"
    gdrive_dao.gdrive_service.files().list.assert_not_called()


def test_get_or_create_folder_existing(gdrive_dao):
    mock_list = MagicMock()
    mock_list.execute.return_value = {"files": [{"id": "found_folder_id", "name": "docs"}]}
    gdrive_dao.gdrive_service.files().list.return_value = mock_list

    folder_id = gdrive_dao._get_or_create_folder("/docs")
    assert folder_id == "found_folder_id"
    assert gdrive_dao._folder_cache["/docs"] == "found_folder_id"


def test_get_or_create_folder_creates_when_not_found(gdrive_dao):
    mock_list = MagicMock()
    mock_list.execute.return_value = {"files": []}
    gdrive_dao.gdrive_service.files().list.return_value = mock_list

    mock_create = MagicMock()
    mock_create.execute.return_value = {"id": "new_created_folder_id"}
    gdrive_dao.gdrive_service.files().create.return_value = mock_create

    folder_id = gdrive_dao._get_or_create_folder("/new_folder")
    assert folder_id == "new_created_folder_id"
    assert gdrive_dao._folder_cache["/new_folder"] == "new_created_folder_id"
    gdrive_dao.gdrive_service.files().create.assert_called_once()


def test_determine_target_folder(gdrive_dao):
    base = Path("/home/user/mydata")
    sub_file = Path("/home/user/mydata/sub/test.txt")
    root_file = Path("/home/user/mydata/test.txt")

    with patch.object(gdrive_dao, "_get_or_create_folder", return_value="sub_id") as mock_get_folder:
        target = gdrive_dao._determine_target_folder(sub_file, "/backup", "default_id", base)
        assert target == "sub_id"
        mock_get_folder.assert_called_once_with("/backup/sub")

    target_root = gdrive_dao._determine_target_folder(root_file, "/backup", "default_id", base)
    assert target_root == "default_id"


def test_upload_files_creates_new_file(gdrive_dao, tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("content")

    with patch.object(gdrive_dao, "_get_or_create_folder", return_value="folder_id"), patch.object(
        gdrive_dao, "_find_existing_file", return_value=None
    ), patch.object(gdrive_dao, "_create_new_file") as mock_create:
        gdrive_dao.upload_files("/remote", [test_file])
        mock_create.assert_called_once_with(test_file, "hello.txt", "folder_id")


def test_upload_files_skips_when_md5_matches(gdrive_dao, tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("content")

    import hashlib
    file_md5 = hashlib.md5(b"content").hexdigest()

    mock_get = MagicMock()
    mock_get.execute.return_value = {"md5Checksum": file_md5}
    gdrive_dao.gdrive_service.files().get.return_value = mock_get

    with patch.object(gdrive_dao, "_get_or_create_folder", return_value="folder_id"), patch.object(
        gdrive_dao, "_find_existing_file", return_value="existing_file_id"
    ):
        gdrive_dao.upload_files("/remote", [test_file])
        gdrive_dao.gdrive_service.files().update.assert_not_called()


def test_upload_files_updates_when_md5_differs(gdrive_dao, tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("content")

    mock_get = MagicMock()
    mock_get.execute.return_value = {"md5Checksum": "different_hash"}
    gdrive_dao.gdrive_service.files().get.return_value = mock_get

    mock_update = MagicMock()
    mock_update.execute.return_value = {"id": "existing_file_id"}
    gdrive_dao.gdrive_service.files().update.return_value = mock_update

    with patch.object(gdrive_dao, "_get_or_create_folder", return_value="folder_id"), patch.object(
        gdrive_dao, "_find_existing_file", return_value="existing_file_id"
    ), patch("googleapiclient.http.MediaFileUpload"):
        gdrive_dao.upload_files("/remote", [test_file])
        gdrive_dao.gdrive_service.files().update.assert_called_once()


def test_upload_files_network_error(gdrive_dao, tmp_path):
    test_file = tmp_path / "hello.txt"
    test_file.write_text("content")

    with patch.object(
        gdrive_dao, "_get_or_create_folder", side_effect=ServerNotFoundError("Server not found")
    ):
        with pytest.raises(NoInternet):
            gdrive_dao.upload_files("/remote", [test_file])
