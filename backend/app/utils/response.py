from typing import Any

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str, data: Any = None, **extra: Any) -> dict[str, Any]:
    response = {
        "success": True,
        "message": message,
        "data": data,
    }
    response.update(extra)
    return response


def error_response(
    message: str,
    data: Any = None,
    status_code: int = 400,
    **extra: Any,
) -> JSONResponse:
    response = {
        "success": False,
        "message": message,
        "data": data,
    }
    response.update(extra)
    return JSONResponse(status_code=status_code, content=jsonable_encoder(response))
