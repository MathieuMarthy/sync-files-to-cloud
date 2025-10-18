class DaoException(Exception):
    """Exception raised for errors in DAO."""

    def __init__(self, message: str):
        super().__init__(message)


class DaoConnectionException(DaoException):
    pass
