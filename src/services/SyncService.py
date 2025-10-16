import logging
import os.path
import re
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
        print(files)

        if self.folder.compress:
            files = [self._compress_files(files)]

        # TODO: upload files to cloud provider

    def _get_files(self) -> list[str]:
        folders_files = Path(self.folder.local_path).rglob("*")

        # Exclude files matching any of the exclude patterns
        if len(self.folder.exclude_patterns) > 0:
            filtered_files = []

            for file in folders_files:
                for pattern in self.folder.exclude_patterns:
                    # Check if the file matches the pattern
                    if not re.match(pattern, str(file.relative_to(self.folder.local_path))):
                        filtered_files.append(file)

            return filtered_files

        return [file.name for file in folders_files]

    def _compress_files(self, files_to_compress: list[str]) -> str:
        # Get the system temp directory
        temp_dir = tempfile.gettempdir()

        # Full path to the zip file
        zip_name = f"{self.folder.name}-{datetime.now().strftime('%d-%m-%y_%I-%M-%S')}.zip"
        zip_path = os.path.join(temp_dir, zip_name)

        # Create the zip file
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file in files_to_compress:
                # Add file with only its basename (not full path)
                zf.write(file, os.path.basename(file))

        return zip_path
