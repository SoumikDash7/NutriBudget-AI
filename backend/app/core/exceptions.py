class AppException(Exception):
    """Base application exception."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class UserAlreadyExistsException(AppException):
    pass


class InvalidCredentialsException(AppException):
    pass


class UserNotFoundException(AppException):
    pass


class UnauthorizedException(AppException):
    pass


class ValidationException(AppException):
    pass