import os.path

import yaml

from src.exceptions.ConfigException import ConfigException
from src.models.sync_parameters import FolderParameter

# Define the root directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


class ProjectConfig:
    _instance = None

    log_level: str = "WARN"
    log_file: str = "app.log"

    def __init__(self):
        self._load_config_yaml()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ProjectConfig, cls).__new__(cls)
        return cls._instance

    def _load_config_yaml(self, file_path: str = "config.yaml"):
        # check if config.yaml exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_path} not found")

        # load the yaml file
        with open(file_path, "r") as config_file:
            config = yaml.safe_load(config_file)

        # load logging configuration if present
        if "logging" in config:
            logging_config = config["logging"]
            self.log_level = logging_config.get("level", self.log_level)
            self.log_file = logging_config.get("file_path", self.log_file)


# Declare the Config class that loads folders configuration from a YAML file
class FoldersConfig:
    folders_parameters: list[FolderParameter]

    def __init__(self):
        self._load_config_yaml()

    def _load_config_yaml(self, file_path: str = "config.yaml"):
        """Load configuration from a YAML file."""

        # check if config.yaml exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_path} not found")

        # load the yaml file
        with open(file_path, "r", encoding="utf-8") as config_file:
            config = yaml.safe_load(config_file)

        # verify if 'sync' section exists
        if "sync" not in config:
            raise ConfigException("'sync' section missing in config.yaml")

        sync_folders = config["sync"]
        # verify if 'sync' section is a non-empty list
        if not isinstance(sync_folders, list) or not sync_folders:
            raise ConfigException("'sync' section must be a non-empty list")

        # parse sync parameters
        self.folders_parameters = []
        for sync_folder in sync_folders:
            self.folders_parameters.append(FolderParameter(**sync_folder))
