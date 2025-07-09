import json

import asyncpg
import ssl
import os
import uuid
import bcrypt
from typing import Optional, Dict, Any
import logging
from datetime import datetime, UTC

logger = logging.getLogger(__name__)


class SupabaseClient:
    def __init__(self):
        self.host = os.getenv("SUPABASE_DB_HOST")
        self.port = os.getenv("SUPABASE_DB_PORT")
        self.database = os.getenv("SUPABASE_DB_NAME")
        self.user = os.getenv("SUPABASE_DB_USER")
        self.password = os.getenv("SUPABASE_DB_PASSWORD")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        missing = []
        for key, value in {
            "SUPABASE_DB_HOST": self.host,
            "SUPABASE_DB_USER": self.user,
            "SUPABASE_DB_PASSWORD": self.password,
            "SUPABASE_DB_NAME": self.database
        }.items():
            if not value:
                missing.append(key)

        if missing:
            raise ValueError(f"Missing environment variables: {missing}")

    async def get_connection(self):
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        return await asyncpg.connect(
            user=self.user,
            password=self.password,
            database=self.database,
            host=self.host,
            port=int(self.port) if self.port else 5432,
            ssl=ssl_context,
            command_timeout=60,
            server_settings={
                'jit': 'off'
            }
        )

    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    async def create_user(self, email: str, password: str, user_metadata: Dict[str, Any]) -> Optional[Dict]:
        """Create a user in Supabase auth.users table"""
        try:
            conn = await self.get_connection()

            hashed_password = self._hash_password(password)

            user_id = str(uuid.uuid4())

            now = datetime.now(UTC)

            query = """
                INSERT INTO auth.users (
                    id,
                    instance_id,
                    email, 
                    encrypted_password, 
                    raw_user_meta_data,
                    created_at,
                    updated_at,
                    email_confirmed_at,
                    last_sign_in_at,
                    role,
                    aud
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING id, email, raw_user_meta_data, created_at
            """

            instance_id = "00000000-0000-0000-0000-000000000000"

            result = await conn.fetchrow(
                query,
                user_id,
                instance_id,
                email,
                hashed_password,
                json.dumps(user_metadata),
                now,
                now,
                now,
                now,
                "authenticated",
                "authenticated"
            )

            await conn.close()

            if result:
                return {
                    "id": str(result["id"]),
                    "email": result["email"],
                    "user_metadata": result["raw_user_meta_data"],
                    "created_at": result["created_at"]
                }
            return None

        except Exception as e:
            logger.error(f"Error creating user in Supabase: {e}")
            return None

    async def authenticate_user(self, email: str, password: str) -> Optional[Dict]:

        try:
            conn = await self.get_connection()

            query = """
                SELECT id, email, encrypted_password, raw_user_meta_data, created_at
                FROM auth.users 
                WHERE email = $1 AND deleted_at IS NULL
            """

            result = await conn.fetchrow(query, email)
            await conn.close()

            if not result:
                return None

            if not self._verify_password(password, result["encrypted_password"]):
                return None

            return {
                "id": str(result["id"]),
                "email": result["email"],
                "user_metadata": result["raw_user_meta_data"],
                "created_at": result["created_at"]
            }

        except Exception as e:
            logger.error(f"Error authenticating user: {e}")
            return None

    async def test_connection(self) -> bool:
        try:
            conn = await self.get_connection()
            await conn.fetchval("SELECT 1")
            await conn.close()
            logger.info("Supabase connection successful")
            return True
        except Exception as e:
            logger.error(f"Supabase connection failed: {e}")
            return False


supabase_client = SupabaseClient()