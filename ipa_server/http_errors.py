"""Helpers para respuestas de error HTTP consistentes."""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from ipa_core.errors import KernelError, ValidationError


def error_response(
    *,
    status_code: int,
    detail: str,
    error_type: str,
    path: str | None = None,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """Construye una respuesta JSON uniforme para errores HTTP."""
    content: dict[str, Any] = {
        "detail": detail,
        "type": error_type,
        "code": status_code,
    }
    if path:
        content["path"] = path
    if extra:
        content.update(extra)
    return JSONResponse(status_code=status_code, content=content)


def from_request(
    request: Request,
    *,
    status_code: int,
    detail: str,
    error_type: str,
    extra: dict[str, Any] | None = None,
) -> JSONResponse:
    """Atajo para incluir la ruta de la request actual."""
    return error_response(
        status_code=status_code,
        detail=detail,
        error_type=error_type,
        path=request.url.path,
        extra=extra,
    )


def validation_error_response(
    request: Request,
    exc: ValidationError,
) -> JSONResponse:
    """Mapea ValidationError a una respuesta consistente."""
    extra: dict[str, Any] = {}
    if exc.error_code:
        extra["error_code"] = exc.error_code
    if exc.context:
        extra["context"] = exc.context
    return from_request(
        request,
        status_code=422,
        detail=str(exc),
        error_type="validation_error",
        extra=extra or None,
    )


def kernel_error_response(request: Request, exc: KernelError) -> JSONResponse:
    """Mapea un KernelError genérico a error 500 consistente."""
    return from_request(
        request,
        status_code=500,
        detail=str(exc),
        error_type="kernel_error",
    )