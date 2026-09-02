from src.dao.cloudDAO import CloudDAO
from src.models.sync_parameters import CloudProvider


def get_clouddao_from_cloud_enum(cloud_provider: CloudProvider) -> CloudDAO:
    match cloud_provider:
        case CloudProvider.GOOGLE_DRIVE:
            from src.dao.gdriveCloudDAO import GDriveCloudDAO

            return GDriveCloudDAO()
        case CloudProvider.GIT:
            from src.dao.gitCloudDAO import GitCloudDAO

            return GitCloudDAO()
        case CloudProvider.PROTON_DRIVE:
            from src.dao.protonDriveCloudDAO import ProtonDriveCloudDAO

            return ProtonDriveCloudDAO()
        case _:
            raise NotImplementedError(
                f"Cloud provider {cloud_provider} not implemented"
            )


