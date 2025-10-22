class NoInternet(Exception):
    pass

class DaoException(Exception):
    """Exception raised for errors in DAO."""

    def __init__(self, message: str):
        super().__init__(message)


class DaoConnectionException(DaoException):
    pass

class NoCredentialFileException(DaoException):
    pass

class AuthentificationRequiredException(DaoException):
    pass
