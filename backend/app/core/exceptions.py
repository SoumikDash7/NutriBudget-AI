class AppException(Exception):
    """Base application exception."""


class UserAlreadyExistsException(AppException):
    pass


class InvalidCredentialsException(AppException):
    pass


class ProfileAlreadyExistsException(AppException):
    pass


class ProfileNotFoundException(AppException):
    pass


class InvalidTokenException(AppException):
    pass


class UnauthorizedException(AppException):
    pass