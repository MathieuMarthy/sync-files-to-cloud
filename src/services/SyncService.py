import logging
import os.path
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

from src.models.sync_parameters import FolderParameter


class SyncService:
    folder: FolderParameter

    def __init__(self, folder: FolderParameter):
        self.folder = folder

    def sync_folder(self):
        logging.info(f"Starting sync for folder: {self.folder.name}")
        files = self._get_files()
        logging.info(f"Found {len(files)} files to sync")

        if self.folder.compress:
            files = [self._compress_files(files)]

        # TODO: upload files to cloud provider

    def _get_files(self) -> list[str]:
        folders_files = Path(self.folder.local_path).rglob("*")

        # Exclude files matching any of the exclude patterns
        if self.folder.exclude_patterns:
            filtered_files = [
                str(file) for file in folders_files
                if not any(pattern in str(file) for pattern in self.folder.exclude_patterns)
            ]
            return filtered_files

        return [str(file) for file in folders_files]

    def _compress_files(self, files_to_compress: list[str]) -> str:
        # Get the system temp directory
        temp_dir = tempfile.gettempdir()

        # Full path to the zip file
        zip_name = f"{self.folder.name}-{datetime.now().strftime('%d-%m-%y_%I-%M-%S')}.zip"
        zip_path = os.path.join(temp_dir, zip_name)

        # Create the zip file
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for file in files_to_compress:
                # Add file with only its basename (not full path)
                zf.write(file, os.path.basename(file))

        return zip_path
