from dataclasses import dataclass
from enum import Enum

from src.exceptions.ConfigException import ConfigInvalidValueException


class CloudProvider(Enum):
    GOOGLE_DRIVE = "GoogleDrive"


@dataclass
class FolderParameter:
    name: str
    cloud_provider: CloudProvider
    sync_interval: int  # in seconds
    compress: bool
    local_path: str
    remote_path: str
    exclude_patterns: list[str]

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
            raise ConfigInvalidValueException("sync_interval must be a positive integer")

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
