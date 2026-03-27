from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings

API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "API key missing", "error_code": "AUTH_MISSING"},
        )
    if api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"success": False, "message": "Invalid API key", "error_code": "AUTH_INVALID"},
        )
    return api_key
