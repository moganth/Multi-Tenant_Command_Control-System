import os
from supabase import create_client, Client
import bcrypt
import logging

logger = logging.getLogger(__name__)

class SupabaseClient:
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_ANON_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL or SUPABASE_ANON_KEY missing in environment.")

        self.supabase: Client = create_client(supabase_url, supabase_key)

    def _hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def create_user(self, email: str, password: str, user_metadata: dict) -> dict:
        """Register user using Supabase Auth API"""
        try:
            response = self.supabase.auth.sign_up(
                {
                    "email": email,
                    "password": password,
                    "options": {
                        "data": user_metadata
                    }
                }
            )
            return response.user
        except Exception as e:
            logger.error(f"Error creating user in Supabase Auth API: {e}")
            return None

    def authenticate_user(self, email: str, password: str) -> dict:
        """Authenticate using Supabase Auth API"""
        try:
            response = self.supabase.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            return response.user
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None

    def insert_user_metadata(self, table: str, data: dict) -> dict:
        """Insert metadata to any Supabase table"""
        try:
            response = self.supabase.table(table).insert(data).execute()
            return response.data
        except Exception as e:
            logger.error(f"Metadata insert failed: {e}")
            return None

    def test_connection(self) -> bool:
        try:
            user = self.supabase.auth.get_user()
            logger.info(f"Supabase Auth user fetched successfully: {user}")
            return True
        except Exception as e:
            logger.error(f"Supabase Auth connection failed: {e}")
            return False


supabase_client = SupabaseClient()
