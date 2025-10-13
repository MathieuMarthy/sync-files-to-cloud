from dataclasses import dataclass


@dataclass
class SyncParameter:
    name: str
    sync_interval: int  # in seconds
    local_path: str
    remote_path: str
    exclude_patterns: list[str]
