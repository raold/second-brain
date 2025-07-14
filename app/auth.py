from fastapi import Request, HTTPException, status
from fastapi.security.utils import get_authorization_scheme_param
from app.config import Config
from app.utils.logger import get_logger

logger = get_logger()

def verify_token(request: Request) -> None:
    """
    Verify the Bearer token from the request headers.
    
    Args:
        request: FastAPI request object
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    authorization: str = request.headers.get("Authorization")
    
    if not authorization:
        logger.warning("Missing Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header"
        )
    
    scheme, token = get_authorization_scheme_param(authorization)
    
    if not token or scheme.lower() != "bearer":
        logger.warning(f"Invalid authorization scheme: {scheme}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme"
        )
    
    if token.strip() not in Config.API_TOKENS:
        logger.warning(f"Unauthorized access attempt with token: {token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )