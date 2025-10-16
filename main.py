import logging
from time import sleep

import schedule

from config import ProjectConfig, FoldersConfig
from src.dao.get_clouddao_from_cloud_enum import get_clouddao_from_cloud_enum
from src.services.SyncService import SyncService

projectConfig = ProjectConfig()

logging.basicConfig(
    level=projectConfig.log_level,
    filename=projectConfig.log_file,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    FoldersConfig = FoldersConfig()

    # Initialize connections for each folder's cloud provider
    # to check if credentials are valid
    for folder in FoldersConfig.folders_parameters:
        logging.info(f"Processing folder: {folder.name}")
        dao = get_clouddao_from_cloud_enum(folder.cloud_provider)
        dao.init_connection()

        # first run
        syncService = SyncService(folder)
        syncService.sync_folder()

        # schedule the sync job
        schedule.every(folder.sync_interval).minutes.do(
            syncService.sync_folder, folder=folder
        )

    while True:
        schedule.run_pending()
        sleep(1)
