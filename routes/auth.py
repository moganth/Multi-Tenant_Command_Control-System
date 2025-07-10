from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from schemas.auth import UserCreate, User, Token
from services.auth_service import auth_service
from handlers.auth_handler import get_current_active_user

router = APIRouter()


@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    user, error_message = await auth_service.create_user(user_data)

    if not user:
        if error_message == "Tenant not found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        elif error_message == "User already exists":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already exists"
            )
        else:
            # Handle any other error (Supabase errors, MongoDB errors, etc.)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message or "Failed to create user"
            )

    return user

@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await auth_service.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await auth_service.create_access_token(user)

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user