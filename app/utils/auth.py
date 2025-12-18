import os, jwt
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError


security = HTTPBearer()
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

if not JWT_SECRET or not JWT_ALGORITHM:
    raise RuntimeError("JWT_SECRET and JWT_ALGORITHM must be set in the environment for search_service")

def decode_jwt(token: str) -> dict:
    try:
        decoded = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded
    except ExpiredSignatureError:
        raise InvalidTokenError("Token expired")
    except InvalidTokenError:
        raise InvalidTokenError("Invalid token")

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = decode_jwt(credentials.credentials)
        return payload["user_id"], credentials.credentials
    except InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=str(e))
