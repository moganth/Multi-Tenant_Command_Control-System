from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from schemas.auth import User, TokenData
from utils.auth import verify_token
from utils.database import get_database

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(credentials.credentials)
    if payload is None:
        raise credentials_exception

    email: str = payload.get("sub")
    tenant_id: str = payload.get("tenant_id")

    if email is None or tenant_id is None:
        raise credentials_exception

    db = await get_database()
    user_doc = await db.users.find_one({"email": email, "tenant_id": tenant_id})

    if user_doc is None:
        raise credentials_exception

    return User(**user_doc, id=user_doc["_id"])


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user