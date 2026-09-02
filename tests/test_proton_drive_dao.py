import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.dao.protonDriveCloudDAO import (
    DEFAULT_CLI_PATH,
    DEFAULT_CONFLICT_STRATEGY,
    ProtonDriveCloudDAO,
)
from src.exceptions.DaoException import (
    AuthentificationRequiredException,
    DaoConnectionException,
    NoInternet,
)


@pytest.fixture
def proton_dao():
    with patch("os.path.exists", return_value=False):
        dao = ProtonDriveCloudDAO()
    return dao


def test_dao_initialization_defaults(proton_dao):
    assert proton_dao.backend == "official_cli"
    assert proton_dao.cli_path == DEFAULT_CLI_PATH
    assert proton_dao.conflict_strategy == DEFAULT_CONFLICT_STRATEGY


def test_dao_load_custom_config():
    custom_json = json.dumps(
        {
            "backend": "official_cli",
            "cli_path": "/usr/bin/custom-proton",
            "conflict_strategy": "skip",
        }
    )
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", pytest.MonkeyPatch().context()
    ):
        with patch("src.utils.path", return_value="credentials/protondrive_credentials.json"):
            with patch("builtins.open", mock_open_helper(custom_json)):
                dao = ProtonDriveCloudDAO()
                assert dao.cli_path == "/usr/bin/custom-proton"
                assert dao.conflict_strategy == "skip"


def mock_open_helper(content):
    import io

    def _open(*args, **kwargs):
        return io.StringIO(content)

    return _open


def test_determine_target_folder_root(proton_dao):
    file = Path("/home/user/docs/file.txt")
    dest = proton_dao._determine_target_folder(file, "/my_remote", None)
    assert dest == "/my_remote"


def test_determine_target_folder_subdir(proton_dao):
    base = Path("/home/user/docs")
    file = Path("/home/user/docs/sub/folder/file.txt")
    dest = proton_dao._determine_target_folder(file, "/my_remote", base)
    assert dest == "/my_remote/sub/folder"


def test_determine_target_folder_subdir_with_root_remote(proton_dao):
    base = Path("/home/user/docs")
    file = Path("/home/user/docs/sub/file.txt")
    dest = proton_dao._determine_target_folder(file, "/", base)
    assert dest == "/sub"


def test_init_connection_cli_not_found(proton_dao):
    with patch("shutil.which", return_value=None), patch("os.path.isfile", return_value=False):
        with pytest.raises(DaoConnectionException) as exc_info:
            proton_dao.init_connection()
        assert "not found in PATH" in str(exc_info.value)


def test_init_connection_success(proton_dao):
    mock_run = MagicMock(returncode=0, stdout="Folder 1\nFolder 2", stderr="")
    with patch("shutil.which", return_value="/bin/proton-drive"), patch(
        "subprocess.run", return_value=mock_run
    ) as mock_subproc:
        proton_dao.init_connection()
        mock_subproc.assert_called_once()
        assert mock_subproc.call_args[0][0] == [
            "proton-drive",
            "filesystem",
            "list",
            "/",
        ]


def test_init_connection_auth_required(proton_dao):
    mock_run = MagicMock(returncode=1, stdout="", stderr="Error: unauthorized, not logged in")
    with patch("shutil.which", return_value="/bin/proton-drive"), patch(
        "subprocess.run", return_value=mock_run
    ):
        with pytest.raises(AuthentificationRequiredException):
            proton_dao.init_connection(can_open_connection_page=False)


def test_init_connection_auth_login_when_allowed(proton_dao):
    mock_check = MagicMock(returncode=1, stdout="", stderr="Error: session expired")
    mock_login = MagicMock(returncode=0, stdout="Login successful", stderr="")

    with patch("shutil.which", return_value="/bin/proton-drive"), patch(
        "subprocess.run", side_effect=[mock_check, mock_login]
    ) as mock_subproc:
        proton_dao.init_connection(can_open_connection_page=True)
        assert mock_subproc.call_count == 2
        assert mock_subproc.call_args_list[1][0][0] == ["proton-drive", "auth", "login"]


def test_init_connection_network_error(proton_dao):
    mock_run = MagicMock(returncode=1, stdout="", stderr="Error: could not resolve host proton.me")
    with patch("shutil.which", return_value="/bin/proton-drive"), patch(
        "subprocess.run", return_value=mock_run
    ):
        with pytest.raises(NoInternet):
            proton_dao.init_connection()


def test_normalize_remote_path(proton_dao):
    assert proton_dao._normalize_remote_path("") == "/my-files"
    assert proton_dao._normalize_remote_path("/") == "/my-files"
    assert proton_dao._normalize_remote_path("/test") == "/my-files/test"
    assert proton_dao._normalize_remote_path("test") == "/my-files/test"
    assert proton_dao._normalize_remote_path("/my-files/test") == "/my-files/test"
    assert proton_dao._normalize_remote_path("/devices/laptop") == "/devices/laptop"


def test_upload_files_empty(proton_dao):
    with patch("subprocess.run") as mock_subproc:
        proton_dao.upload_files("/remote", [])
        mock_subproc.assert_not_called()


def test_upload_files_success(proton_dao, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello proton")

    proton_dao._folder_cache.add("/my-files/remote")
    proton_dao._folder_cache.add("/my-files/remote/dir")
    mock_run = MagicMock(returncode=0, stdout="uploaded", stderr="")

    with patch("subprocess.run", return_value=mock_run) as mock_subproc:
        proton_dao.upload_files("/remote/dir", [test_file])
        mock_subproc.assert_called_once()
        args = mock_subproc.call_args[0][0]
        assert args == [
            "proton-drive",
            "filesystem",
            "upload",
            "-f",
            "replace",
            "-d",
            "merge",
            str(test_file),
            "/my-files/remote/dir",
        ]


def test_upload_files_network_error(proton_dao, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("data")

    proton_dao._folder_cache.add("/my-files/remote")
    mock_run = MagicMock(returncode=1, stdout="", stderr="Error: network is unreachable")
    with patch("subprocess.run", return_value=mock_run):
        with pytest.raises(NoInternet):
            proton_dao.upload_files("/remote", [test_file])


def test_upload_files_auth_expired(proton_dao, tmp_path):
    test_file = tmp_path / "test.txt"
    test_file.write_text("data")

    proton_dao._folder_cache.add("/my-files/remote")
    mock_run = MagicMock(returncode=1, stdout="", stderr="Error: token expired, login required")
    with patch("subprocess.run", return_value=mock_run):
        with pytest.raises(AuthentificationRequiredException):
            proton_dao.upload_files("/remote", [test_file])



def test_upload_files_rclone(tmp_path):
    test_file = tmp_path / "doc.txt"
    test_file.write_text("rclone content")

    dao = ProtonDriveCloudDAO()
    dao.backend = "rclone"
    dao.rclone_path = "rclone"
    dao.rclone_remote = "myproton"

    mock_run = MagicMock(returncode=0, stdout="", stderr="")
    with patch("subprocess.run", return_value=mock_run) as mock_subproc:
        dao.upload_files("/remote/folder", [test_file])
        mock_subproc.assert_called_once()
        args = mock_subproc.call_args[0][0]
        assert args == [
            "rclone",
            "copyto",
            str(test_file),
            "myproton:remote/folder/doc.txt",
        ]


def test_ensure_folder_exists_creates_missing_folders(proton_dao):
    # Simulate /my-files/new_dir does not exist, so info fails, then create-folder succeeds
    info_fail = MagicMock(returncode=1, stdout="", stderr="Node not found: new_dir")
    create_ok = MagicMock(returncode=0, stdout="", stderr="")

    with patch("subprocess.run", side_effect=[info_fail, create_ok]) as mock_subproc:
        proton_dao._ensure_folder_exists("/my-files/new_dir")
        assert mock_subproc.call_count == 2
        assert mock_subproc.call_args_list[0][0][0] == [
            "proton-drive",
            "filesystem",
            "info",
            "/my-files/new_dir",
        ]
        assert mock_subproc.call_args_list[1][0][0] == [
            "proton-drive",
            "filesystem",
            "create-folder",
            "/my-files",
            "new_dir",
        ]
        assert "/my-files/new_dir" in proton_dao._folder_cache


def test_download_files_not_implemented(proton_dao):
    with pytest.raises(NotImplementedError):
        proton_dao.download_files()

