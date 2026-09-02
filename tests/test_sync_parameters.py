import pytest

from src.dao.get_clouddao_from_cloud_enum import get_clouddao_from_cloud_enum
from src.dao.protonDriveCloudDAO import ProtonDriveCloudDAO
from src.exceptions.ConfigException import ConfigInvalidValueException
from src.models.sync_parameters import CloudProvider, FolderParameter


def test_cloud_provider_proton_drive_enum():
    assert CloudProvider.PROTON_DRIVE.value == "ProtonDrive"
    assert CloudProvider("ProtonDrive") == CloudProvider.PROTON_DRIVE


def test_folder_parameter_with_proton_drive_string():
    folder = FolderParameter(
        name="test_proton",
        cloud_provider="ProtonDrive",
        sync_interval=60,
        compress=True,
        local_path="/tmp/test",
        remote_path="/backups",
        exclude_patterns=[],
    )
    assert folder.cloud_provider == CloudProvider.PROTON_DRIVE
    assert folder.name == "test_proton"


def test_folder_parameter_with_proton_drive_enum():
    folder = FolderParameter(
        name="test_proton",
        cloud_provider=CloudProvider.PROTON_DRIVE,
        sync_interval=60,
        compress=False,
        local_path="/tmp/test",
        remote_path="/backups",
        exclude_patterns=[],
    )
    assert folder.cloud_provider == CloudProvider.PROTON_DRIVE


def test_get_clouddao_from_cloud_enum_returns_proton_drive():
    dao = get_clouddao_from_cloud_enum(CloudProvider.PROTON_DRIVE)
    assert isinstance(dao, ProtonDriveCloudDAO)


def test_folder_parameter_invalid_provider():
    with pytest.raises(ConfigInvalidValueException):
        FolderParameter(
            name="invalid",
            cloud_provider="InvalidCloud",
            sync_interval=60,
            compress=True,
            local_path="/tmp/test",
            remote_path="/backups",
            exclude_patterns=[],
        )


def test_folders_config_with_proton_drive(tmp_path, monkeypatch):
    import io
    from unittest.mock import patch
    from config import FoldersConfig

    sample_yaml = """
sync:
  - name: my_proton_backup
    cloud_provider: "ProtonDrive"
    sync_interval: 30
    compress: true
    local_path: "/home/user/vault"
    remote_path: "/vault"
    exclude_patterns:
      - "*.tmp"
"""
    with patch("os.path.exists", return_value=True), patch(
        "builtins.open", return_value=io.StringIO(sample_yaml)
    ):
        config = FoldersConfig()
        assert len(config.folders_parameters) == 1
        param = config.folders_parameters[0]
        assert param.name == "my_proton_backup"
        assert param.cloud_provider == CloudProvider.PROTON_DRIVE
        assert param.sync_interval == 30
        assert param.compress is True
        assert param.remote_path == "/vault"

