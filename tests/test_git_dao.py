import io
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from git.exc import GitCommandError

from src.dao.gitCloudDAO import GitCloudDAO
from src.exceptions.DaoException import (
    AuthentificationRequiredException,
    DaoConnectionException,
    NoCredentialFileException,
    NoInternet,
)


@pytest.fixture
def git_dao():
    return GitCloudDAO()


def test_init_connection_missing_credentials(git_dao):
    with patch("os.path.exists", return_value=False):
        with pytest.raises(NoCredentialFileException) as exc_info:
            git_dao.init_connection()
        assert "missing credentials file" in str(exc_info.value)


def test_init_connection_invalid_json(git_dao):
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", return_value=io.StringIO("invalid json")
    ):
        with pytest.raises(NoCredentialFileException) as exc_info:
            git_dao.init_connection()
        assert "invalid credentials JSON" in str(exc_info.value)


def test_init_connection_missing_repo_url(git_dao):
    creds_json = json.dumps({"auth_type": "none"})
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", return_value=io.StringIO(creds_json)
    ):
        with pytest.raises(NoCredentialFileException) as exc_info:
            git_dao.init_connection()
        assert "repository_url' is missing" in str(exc_info.value)


def test_init_connection_ssh_key_missing(git_dao):
    creds_json = json.dumps(
        {
            "repository_url": "git@github.com:user/repo.git",
            "auth_type": "ssh",
            "ssh_key_path": "/path/to/nonexistent/id_rsa",
        }
    )

    def mock_exists(p):
        if str(p).endswith("id_rsa"):
            return False
        return True

    with patch("os.path.exists", side_effect=mock_exists), patch(
        "builtins.open", return_value=io.StringIO(creds_json)
    ):
        with pytest.raises(DaoConnectionException) as exc_info:
            git_dao.init_connection()
        assert "SSH key file not found" in str(exc_info.value)


def test_init_connection_ssh_success(git_dao):
    creds_json = json.dumps(
        {
            "repository_url": "git@github.com:user/repo.git",
            "auth_type": "ssh",
            "ssh_key_path": "/path/to/key",
            "branch": "main",
        }
    )
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", return_value=io.StringIO(creds_json)
    ), patch("pathlib.Path.exists", return_value=False), patch(
        "src.dao.gitCloudDAO.os.makedirs"
    ), patch(
        "git.Repo.clone_from"
    ) as mock_clone:
        mock_repo = MagicMock()
        mock_clone.return_value = mock_repo
        git_dao.init_connection()

        assert git_dao.repo_url == "git@github.com:user/repo.git"
        assert "ssh -i \"/path/to/key\"" in git_dao.git_env["GIT_SSH_COMMAND"]
        mock_clone.assert_called_once()



def test_init_connection_token_missing_raises_auth_required(git_dao):
    creds_json = json.dumps(
        {
            "repository_url": "https://github.com/user/repo.git",
            "auth_type": "token",
            "token": "",
        }
    )
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", return_value=io.StringIO(creds_json)
    ):
        with pytest.raises(AuthentificationRequiredException):
            git_dao.init_connection(can_open_connection_page=False)


def test_init_connection_token_missing_with_connection_page(git_dao):
    creds_json = json.dumps(
        {
            "repository_url": "https://github.com/user/repo.git",
            "auth_type": "token",
            "token": "",
        }
    )
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", return_value=io.StringIO(creds_json)
    ):
        with pytest.raises(DaoConnectionException) as exc_info:
            git_dao.init_connection(can_open_connection_page=True)
        assert "'token' parameter is missing" in str(exc_info.value)


def test_get_token_url(git_dao):
    url = "https://github.com/owner/repo.git"
    token_url = git_dao._get_token_url(url, "myuser", "mytoken123")
    assert token_url == "https://myuser:mytoken123@github.com/owner/repo.git"

    # With default username
    token_url_default = git_dao._get_token_url(url, "", "mytoken123")
    assert token_url_default == "https://oauth2:mytoken123@github.com/owner/repo.git"


def test_init_connection_network_error(git_dao):
    creds_json = json.dumps(
        {"repository_url": "https://github.com/user/repo.git", "auth_type": "none"}
    )
    err = GitCommandError("clone", "fatal: Could not resolve host: github.com")
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", return_value=io.StringIO(creds_json)
    ), patch("pathlib.Path.exists", return_value=False), patch(
        "src.dao.gitCloudDAO.os.makedirs"
    ), patch(
        "git.Repo.clone_from", side_effect=err
    ):
        with pytest.raises(NoInternet):
            git_dao.init_connection()


def test_init_connection_auth_failed_error(git_dao):
    creds_json = json.dumps(
        {"repository_url": "https://github.com/user/repo.git", "auth_type": "none"}
    )
    err = GitCommandError("clone", "fatal: Authentication failed for 'https://...'")
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", return_value=io.StringIO(creds_json)
    ), patch("pathlib.Path.exists", return_value=False), patch(
        "src.dao.gitCloudDAO.os.makedirs"
    ), patch(
        "git.Repo.clone_from", side_effect=err
    ):
        with pytest.raises(AuthentificationRequiredException):
            git_dao.init_connection(can_open_connection_page=False)



def test_upload_files_not_initialized(git_dao):
    with pytest.raises(DaoConnectionException) as exc_info:
        git_dao.upload_files("/remote", [Path("/tmp/file.txt")])
    assert "connection not initialized" in str(exc_info.value)


def test_upload_files_no_changes(git_dao, tmp_path):
    git_dao.repo = MagicMock()
    git_dao.local_repo_path = tmp_path / "repo"
    git_dao.local_repo_path.mkdir(parents=True, exist_ok=True)

    # Empty git status (no modified files)
    git_dao.repo.git.status.return_value = ""

    src_file = tmp_path / "test.txt"
    src_file.write_text("content")

    git_dao.upload_files("backups", [src_file])

    git_dao.repo.git.add.assert_called_once()
    git_dao.repo.git.commit.assert_not_called()
    git_dao.repo.git.push.assert_not_called()


def test_upload_files_with_changes_commits_and_pushes(git_dao, tmp_path):
    git_dao.repo = MagicMock()
    git_dao.local_repo_path = tmp_path / "repo"
    git_dao.local_repo_path.mkdir(parents=True, exist_ok=True)
    git_dao.branch = "main"
    git_dao.author_name = "Test Bot"
    git_dao.author_email = "bot@test.local"
    git_dao.repo_url = "https://github.com/user/repo.git"

    # Non-empty git status (changes detected)
    git_dao.repo.git.status.return_value = " M test.txt"

    src_file = tmp_path / "test.txt"
    src_file.write_text("new content")

    git_dao.upload_files("backups", [src_file])

    git_dao.repo.git.add.assert_called_once()
    git_dao.repo.git.commit.assert_called_once()
    commit_author = git_dao.repo.git.commit.call_args[0][2]
    assert "Test Bot <bot@test.local>" in commit_author
    git_dao.repo.git.push.assert_called_once_with("-u", "origin", "main")


def test_upload_files_skips_identical_md5(git_dao, tmp_path):
    git_dao.repo = MagicMock()
    git_dao.local_repo_path = tmp_path / "repo"
    git_dao.local_repo_path.mkdir(parents=True, exist_ok=True)
    git_dao.repo.git.status.return_value = ""

    src_file = tmp_path / "test.txt"
    src_file.write_text("same content")

    dest_file = git_dao.local_repo_path / "test.txt"
    dest_file.write_text("same content")

    with patch("shutil.copy2") as mock_copy:
        git_dao.upload_files("", [src_file])
        mock_copy.assert_not_called()


def test_download_files_not_implemented(git_dao):
    with pytest.raises(NotImplementedError):
        git_dao.download_files()
