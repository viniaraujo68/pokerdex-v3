"""User-facing API errors carry a stable machine `code` next to the pt-BR `message`.

The frontend localizes off `code` (`apiError.<code>` in its dictionaries) and falls back to
`message`, so API consumers without a dictionary still get readable text. Only errors a user
can actually act on get codes — 404s and "not authenticated" stay plain strings.
"""
from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str) -> HTTPException:
    """HTTPException whose `detail` is `{"code": ..., "message": ...}`."""
    return HTTPException(status_code, {"code": code, "message": message})


def error_body(code: str, message: str) -> dict:
    """Same shape, for handlers that build a JSONResponse instead of raising."""
    return {"detail": {"code": code, "message": message}}
