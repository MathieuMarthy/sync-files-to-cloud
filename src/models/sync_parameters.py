from dataclasses import dataclass
from enum import Enum

from src.exceptions.ConfigException import ConfigInvalidValueException


class CloudProvider(Enum):
    GOOGLE_DRIVE = "GoogleDrive"
    GIT = "Git"
    PROTON_DRIVE = "ProtonDrive"



@dataclass
class FolderParameter:
    name: str
    cloud_provider: CloudProvider
    sync_interval: int  # in seconds
    compress: bool
    local_path: str | list[str]
    remote_path: str
    exclude_patterns: list[str]
    repository_url: str | None = None
    branch: str | None = "main"

    def __post_init__(self):
        """Validate fields"""

        # field: cloud provider
        if not isinstance(self.cloud_provider, CloudProvider):

            if isinstance(self.cloud_provider, str):
                try:
                    # try to convert string to CloudProvider enum
                    self.cloud_provider = CloudProvider(self.cloud_provider)
                except ValueError:
                    valid_values = [e.value for e in CloudProvider]
                    raise ConfigInvalidValueException(
                        f"Invalid cloud_provider '{self.cloud_provider}'. "
                        f"Must be one of: {valid_values}"
                    )
            else:
                raise ConfigInvalidValueException(
                    f"cloud_provider must be a CloudProvider a string, "
                    f"got {type(self.cloud_provider).__name__}"
                )

        # field: sync_interval
        if not isinstance(self.sync_interval, int) or self.sync_interval <= 0:
            raise ConfigInvalidValueException(
                "sync_interval must be a positive integer"
            )

        # field: compress
        if not isinstance(self.compress, bool):
            if isinstance(self.compress, str):
                if self.compress.lower() in ["true", "yes", "1"]:
                    self.compress = True
                elif self.compress.lower() in ["false", "no", "0"]:
                    self.compress = False
                else:
                    raise ConfigInvalidValueException(
                        f"Invalid compress value '{self.compress}'. Must be a boolean."
                    )

        # field: local_path
        if not isinstance(self.local_path, (str, list)):
            raise ConfigInvalidValueException(
                f"local_path must be a string or a list of strings, "
                f"got {type(self.local_path).__name__}"
            )

        if isinstance(self.local_path, list):
            if not all(isinstance(item, str) for item in self.local_path):
                raise ConfigInvalidValueException(
                    "All items in local_path list must be strings"
                )
