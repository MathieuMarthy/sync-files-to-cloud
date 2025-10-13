class ConfigException(Exception):
    """Exception raised for errors in the configuration."""

    def __init__(self, message: str):
        super().__init__(message)
