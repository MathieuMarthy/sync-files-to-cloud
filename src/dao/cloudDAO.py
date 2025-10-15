from abc import ABC

from src.dao.gdriveCloudDAO import GDriveCloudDAO
from src.models.sync_parameters import CloudProvider


class CloudDAO(ABC):
    def upload_files(self):
        pass

    def download_files(self):
        pass

    @staticmethod
    def get_clouddao_from_cloud_enum(cloud_provider: CloudProvider) -> "CloudDAO":
        match cloud_provider:
            case CloudProvider.GOOGLE_DRIVE:
                return GDriveCloudDAO()
            case _:
                raise NotImplementedError(f"Cloud provider {cloud_provider} not implemented")
