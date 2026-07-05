from typing import Any


def success_response(
    data: Any = None,
    message: str = "Success",
):
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def error_response(
    message: str,
    errors: Any = None,
):
    return {
        "success": False,
        "message": message,
        "errors": errors,
    }