import asyncio
import logging
import threading
from time import sleep

import schedule

from config import ProjectConfig, FoldersConfig
from src.dao.get_clouddao_from_cloud_enum import get_clouddao_from_cloud_enum
from src.exceptions.DaoException import AuthentificationRequiredException
from src.models.sync_parameters import FolderParameter
from src.services.NotificationService import NotificationService
from src.services.SyncService import SyncService

projectConfig = ProjectConfig()

logging.basicConfig(
    level=projectConfig.log_level,
    filename=projectConfig.log_file,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Global event loop for async operations
event_loop = None


def start_event_loop(loop):
    """Start the event loop in a separate thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def start_sync_folder(folder: FolderParameter, is_second_attempt: bool = False):
    sync_service = SyncService(folder)

    try:
        sync_service.sync_folder()
    except AuthentificationRequiredException:
        if is_second_attempt:
            logging.error(
                f"Reconnection attempt failed for folder: {folder.name}. Check credentials."
            )
        else:
            logging.info(
                f"Failed to connect to cloud provider for folder: {folder.name}, send a notification to reconnect"
            )

            # Use asyncio.run_coroutine_threadsafe to run the async notification
            asyncio.run_coroutine_threadsafe(
                NotificationService.send_reconnection_notification(
                    folder.cloud_provider,
                    lambda: reconnect_and_sync(folder)
                ),
                event_loop
            )
    except Exception as e:
        logging.error(f"An unexpected error occurred during sync for folder: {folder.name}. Error: {str(e)}")
        asyncio.run_coroutine_threadsafe(
            NotificationService.send_error_notification(f"Error syncing folder '{folder.name}'. Check logs for details."),
            event_loop
        )

def reconnect_and_sync(folder: FolderParameter):
    dao = get_clouddao_from_cloud_enum(folder.cloud_provider)
    dao.init_connection(can_open_connection_page=True)

    start_sync_folder(folder, is_second_attempt=True)


def main():
    global event_loop

    # Create and start the event loop in a separate thread
    event_loop = asyncio.new_event_loop()
    loop_thread = threading.Thread(target=start_event_loop, args=(event_loop,), daemon=True)
    loop_thread.start()

    folders_config = FoldersConfig()

    # Initialize connections for each folder's cloud provider
    # to check if credentials are valid
    for folder_config in folders_config.folders_parameters:
        # first run
        start_sync_folder(folder_config)

        # schedule the sync job
        schedule.every(folder_config.sync_interval).minutes.do(
            start_sync_folder, folder=folder_config
        )

    try:
        while True:
            schedule.run_pending()
            sleep(1)
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        event_loop.call_soon_threadsafe(event_loop.stop)


if __name__ == "__main__":
    main()
