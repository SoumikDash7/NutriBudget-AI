from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    AppException,
    InvalidCredentialsException,
    ProfileNotFoundException,
    UserAlreadyExistsException,
)
from app.utils.responses import error_response


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(UserAlreadyExistsException)
    async def user_exists_handler(
        request: Request,
        exc: UserAlreadyExistsException,
    ):
        return JSONResponse(
            status_code=400,
            content=error_response(
                message="User already exists.",
            ),
        )

    @app.exception_handler(ProfileNotFoundException)
    async def profile_not_found_handler(
        request: Request,
        exc: ProfileNotFoundException,
    ):
        return JSONResponse(
            status_code=404,
            content=error_response(
                message="Profile not found.",
            ),
        )

    @app.exception_handler(InvalidCredentialsException)
    async def invalid_credentials_handler(
        request: Request,
        exc: InvalidCredentialsException,
    ):
        return JSONResponse(
            status_code=401,
            content=error_response(
                message="Invalid credentials.",
            ),
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request,
        exc: AppException,
    ):
        return JSONResponse(
            status_code=400,
            content=error_response(
                message=str(exc),
            ),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request,
        exc: Exception,
    ):
        # Do not swallow FastAPI's own HTTP and validation exceptions
        if isinstance(exc, (HTTPException, RequestValidationError)):
            raise exc
        return JSONResponse(
            status_code=500,
            content=error_response(
                message="Internal Server Error",
            ),
        )