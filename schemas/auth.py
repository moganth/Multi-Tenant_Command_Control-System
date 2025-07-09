from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    tenant_id: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None
    tenant_id: Optional[str] = None

class User(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    tenant_id: str
    is_active: bool = True
    created_at: datetime
    updated_at: datetime