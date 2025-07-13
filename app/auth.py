# app/auth.py
import os
from fastapi import Request, HTTPException
from fastapi.security.utils import get_authorization_scheme_param

API_TOKENS = set(os.getenv("API_TOKENS", "").split(","))

def verify_token(request: Request):
    authorization: str = request.headers.get("Authorization")
    scheme, token = get_authorization_scheme_param(authorization)

    if not token or scheme.lower() != "bearer" or token.strip() not in API_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
