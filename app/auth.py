from fastapi import Request, HTTPException
from fastapi.security.utils import get_authorization_scheme_param
from app.config import Config
import logging

logger = logging.getLogger(__name__)

def verify_token(request: Request):
    authorization: str = request.headers.get("Authorization")
    scheme, token = get_authorization_scheme_param(authorization)

    if not token or scheme.lower() != "bearer" or token.strip() not in Config.API_TOKENS:
        logger.warning(f"Unauthorized access attempt with token: {token}")
        raise HTTPException(status_code=401, detail="Invalid or missing token")