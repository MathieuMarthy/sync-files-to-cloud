from src.dao.cloudDAO import CloudDAO
from src.dao.gdriveCloudDAO import GDriveCloudDAO
from src.models.sync_parameters import CloudProvider


def get_clouddao_from_cloud_enum(cloud_provider: CloudProvider) -> CloudDAO:
    match cloud_provider:
        case CloudProvider.GOOGLE_DRIVE:
            GDriveCloudDAO.init_connection()
            return GDriveCloudDAO()
        case _:
            raise NotImplementedError(f"Cloud provider {cloud_provider} not implemented")
