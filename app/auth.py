from fastapi import HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param

<<<<<<< HEAD
from app.config import Config
=======
from app.config import config
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
from app.utils.logger import logger


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
    if not verify_token_str(token):
        logger.warning(f"Unauthorized access attempt with token: {token[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )

def verify_token_str(token: str) -> bool:
    """
    Directly verify a token string (for WebSocket or internal use).
    Returns True if valid, False otherwise.
    """
    if not token:
        return False
<<<<<<< HEAD
    tokens = Config.API_TOKENS
=======
    tokens = config.api_tokens
>>>>>>> a7482b9e847b5f65dc4124534881b2b3c3814b01
    if isinstance(tokens, set):
        tokens = list(tokens)
    return token.strip() in tokens