import logging

from config import Config
from src.dao.get_clouddao_from_cloud_enum import get_clouddao_from_cloud_enum

config = Config()

logging.basicConfig(
    level=config.log_level,
    filename=config.log_file,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

if __name__ == "__main__":
    for folder_to_sync in config.sync_parameters:
        dao = get_clouddao_from_cloud_enum(folder_to_sync.cloud_provider)
        print(dao)
