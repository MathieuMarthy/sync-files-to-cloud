import logging
from typing import Callable

from desktop_notifier import DesktopNotifier, Button

from src.models.sync_parameters import CloudProvider


class NotificationService:
    notifier = DesktopNotifier(app_name="Sync Files")

    @staticmethod
    async def send_reconnection_notification(cloud_provider: CloudProvider, reconnect_function: Callable = None):
        logging.debug(f"Sending reconnection notification for {cloud_provider.value}")
        await NotificationService.notifier.send(
            title="Reconnection Required",
            message=f"Please reconnect to {cloud_provider.value} to continue syncing files.",
            buttons=[
                Button(
                    title="Reconnect",
                    on_pressed=reconnect_function,
                )
            ]
        )
