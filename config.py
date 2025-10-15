import os.path

import yaml

from src.exceptions.ConfigException import ConfigException
from src.models.sync_parameters import SyncParameter

# Define the root directory
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


# Declare the Config class that loads configuration from a YAML file
class Config:
    _instance = None

    sync_parameters: list[SyncParameter]

    log_level: str = "WARN"
    log_file: str = "logs/app.log"

    # Singleton pattern implementation
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        self._load_config_yaml()

    def _load_config_yaml(self, file_path: str = "config.yaml"):
        """Load configuration from a YAML file."""

        # check if config.yaml exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"{file_path} not found")

        # load the yaml file
        with open(file_path, "r") as config_file:
            config = yaml.safe_load(config_file)

        # verify if 'sync' section exists
        if "sync" not in config:
            raise ConfigException("'sync' section missing in config.yaml")

        sync_folders = config["sync"]
        # verify if 'sync' section is a non-empty list
        if not isinstance(sync_folders, list) or not sync_folders:
            raise ConfigException("'sync' section must be a non-empty list")

        # parse sync parameters
        self.sync_parameters = []
        for sync_folder in sync_folders:
            self.sync_parameters.append(SyncParameter(**sync_folder))

        # load logging configuration if present
        if "logging" in config:
            logging_config = config["logging"]
            self.log_level = logging_config.get("level", self.log_level)
            self.log_file = logging_config.get("file", self.log_file)
