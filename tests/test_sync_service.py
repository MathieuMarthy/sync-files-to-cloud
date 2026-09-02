import os
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.exceptions.DaoException import NoInternet
from src.models.sync_parameters import CloudProvider, FolderParameter
from src.services.SyncService import SyncService


@pytest.fixture
def make_folder():
    def _create(
        name="test_sync",
        cloud_provider=CloudProvider.PROTON_DRIVE,
        sync_interval=60,
        compress=False,
        local_path="/tmp",
        remote_path="/backups",
        exclude_patterns=None,
    ):
        return FolderParameter(
            name=name,
            cloud_provider=cloud_provider,
            sync_interval=sync_interval,
            compress=compress,
            local_path=local_path,
            remote_path=remote_path,
            exclude_patterns=exclude_patterns or [],
        )

    return _create


def test_get_files_single_directory(make_folder, tmp_path):
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.log"
    sub = tmp_path / "sub"
    sub.mkdir()
    f3 = sub / "file3.txt"

    f1.write_text("1")
    f2.write_text("2")
    f3.write_text("3")

    folder = make_folder(local_path=str(tmp_path), exclude_patterns=[])
    service = SyncService(folder)
    files = service._get_files()

    assert len(files) == 3
    file_names = {f.name for f in files}
    assert file_names == {"file1.txt", "file2.log", "file3.txt"}


def test_get_files_with_exclude_patterns(make_folder, tmp_path):
    f1 = tmp_path / "keep.txt"
    f2 = tmp_path / "ignore.tmp"
    f3 = tmp_path / "cache.log"
    sub = tmp_path / "node_modules"
    sub.mkdir()
    f4 = sub / "package.json"

    f1.write_text("keep")
    f2.write_text("tmp")
    f3.write_text("log")
    f4.write_text("pkg")

    folder = make_folder(
        local_path=str(tmp_path),
        exclude_patterns=["*.tmp", "*.log", "node_modules/*"],
    )
    service = SyncService(folder)
    files = service._get_files()

    assert len(files) == 1
    assert files[0].name == "keep.txt"


def test_get_files_multiple_directories(make_folder, tmp_path):
    dir1 = tmp_path / "dir1"
    dir2 = tmp_path / "dir2"
    dir1.mkdir()
    dir2.mkdir()

    (dir1 / "a.txt").write_text("a")
    (dir2 / "b.txt").write_text("b")

    folder = make_folder(local_path=[str(dir1), str(dir2)])
    service = SyncService(folder)
    files = service._get_files()

    assert len(files) == 2
    assert {f.name for f in files} == {"a.txt", "b.txt"}


def test_get_files_nonexistent_directory(make_folder):
    folder = make_folder(local_path="/path/that/definitely/does/not/exist")
    service = SyncService(folder)
    files = service._get_files()
    assert files == []


def test_compress_files(make_folder, tmp_path):
    f1 = tmp_path / "hello.txt"
    f1.write_text("hello world")

    folder = make_folder(local_path=str(tmp_path), compress=True)
    service = SyncService(folder)

    zip_path = service._compress_files([f1])
    assert os.path.exists(zip_path)
    assert zip_path.endswith(f"{folder.name}.zip")

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "hello.txt" in namelist


def test_sync_folder_no_files_exits_early(make_folder, tmp_path):
    folder = make_folder(local_path=str(tmp_path))
    service = SyncService(folder)

    mock_dao = MagicMock()
    with patch(
        "src.services.SyncService.get_clouddao_from_cloud_enum",
        return_value=mock_dao,
    ):
        service.sync_folder()
        mock_dao.init_connection.assert_called_once()
        mock_dao.upload_files.assert_not_called()


def test_sync_folder_uncompressed(make_folder, tmp_path):
    f1 = tmp_path / "data.txt"
    f1.write_text("content")

    folder = make_folder(local_path=str(tmp_path), compress=False)
    service = SyncService(folder)

    mock_dao = MagicMock()
    with patch(
        "src.services.SyncService.get_clouddao_from_cloud_enum",
        return_value=mock_dao,
    ):
        service.sync_folder()
        mock_dao.init_connection.assert_called_once()
        mock_dao.upload_files.assert_called_once()
        args = mock_dao.upload_files.call_args[0]
        assert args[0] == folder.remote_path
        assert args[1] == [f1]
        assert args[2] == Path(folder.local_path)


def test_sync_folder_compressed(make_folder, tmp_path):
    f1 = tmp_path / "data.txt"
    f1.write_text("content")

    folder = make_folder(local_path=str(tmp_path), compress=True)
    service = SyncService(folder)

    mock_dao = MagicMock()
    with patch(
        "src.services.SyncService.get_clouddao_from_cloud_enum",
        return_value=mock_dao,
    ):
        service.sync_folder()
        mock_dao.init_connection.assert_called_once()
        mock_dao.upload_files.assert_called_once()
        args = mock_dao.upload_files.call_args[0]
        assert args[0] == folder.remote_path
        assert len(args[1]) == 1
        assert str(args[1][0]).endswith(".zip")
        assert args[2] is None


def test_sync_folder_handles_no_internet(make_folder, tmp_path):
    f1 = tmp_path / "data.txt"
    f1.write_text("content")

    folder = make_folder(local_path=str(tmp_path))
    service = SyncService(folder)

    mock_dao = MagicMock()
    mock_dao.upload_files.side_effect = NoInternet("network down")

    with patch(
        "src.services.SyncService.get_clouddao_from_cloud_enum",
        return_value=mock_dao,
    ):
        # Should catch NoInternet and log error without raising unhandled exception
        service.sync_folder()
        mock_dao.upload_files.assert_called_once()
