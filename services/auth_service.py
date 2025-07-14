from typing import Optional
from datetime import datetime, timedelta, UTC
from schemas.auth import UserCreate, User, Token
from utils.auth import create_access_token
from utils.database import get_database
from utils.supabase_client import supabase_client
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)


class AuthService:
    async def create_user(self, user_data: UserCreate) -> tuple[Optional[User], Optional[str]]:
        db = await get_database()

        # Validate tenant exists FIRST
        tenant = await db.tenants.find_one({"_id": user_data.tenant_id})
        if not tenant:
            logger.error(f"Tenant {user_data.tenant_id} not found")
            return None, "Tenant not found"

        # Check if user already exists in MongoDB
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            logger.warning(f"User with email {user_data.email} already exists")
            return None, "User already exists"

        # Create user in Supabase with proper error handling
        try:
            supabase_response = supabase_client.create_user(
                user_data.email,
                user_data.password,
                {"full_name": user_data.full_name, "tenant_id": user_data.tenant_id}
            )

            if not supabase_response:
                logger.error("Failed to create user in Supabase")
                return None, "Failed to create user in Supabase"

        except Exception as e:
            error_message = str(e)
            logger.error(f"Error creating user in Supabase: {error_message}")

            # Check if it's a duplicate email error
            if "duplicate key value" in error_message and "users_email" in error_message:
                return None, "User already exists"
            else:
                return None, f"Failed to create user in Supabase: {error_message}"

        # Create user in MongoDB
        user_doc = {
            "_id": str(ObjectId()),
            "email": user_data.email,
            "full_name": user_data.full_name,
            "tenant_id": user_data.tenant_id,
            "is_active": True,
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC)
        }

        try:
            await db.users.insert_one(user_doc)
            logger.info(f"User created successfully: {user_data.email}")
            return User(**user_doc, id=user_doc["_id"]), None
        except Exception as e:
            logger.error(f"Failed to create user in MongoDB: {e}")
            return None, f"Failed to create user in MongoDB: {str(e)}"
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        db = await get_database()

        # Authenticate with Supabase
        supabase_response = supabase_client.authenticate_user(email, password)
        if not supabase_response:
            logger.warning(f"Authentication failed for user: {email}")
            return None

        # Get user from MongoDB
        user_doc = await db.users.find_one({"email": email})
        if not user_doc:
            logger.warning(f"User not found in MongoDB: {email}")
            return None

        return User(**user_doc, id=user_doc["_id"])

    async def create_access_token(self, user: User) -> Token:
        # You'll need to import settings or define ACCESS_TOKEN_EXPIRE_MINUTES
        access_token_expires = timedelta(minutes=30)  # Default to 30 minutes
        access_token = create_access_token(
            data={"sub": user.email, "tenant_id": user.tenant_id},
            expires_delta=access_token_expires
        )

        return Token(access_token=access_token, token_type="bearer")

auth_service = AuthService()