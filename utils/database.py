from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
from config import settings


class Database:
    client: Optional[AsyncIOMotorClient] = None


db = Database()


async def get_database():
    return db.client[settings.DATABASE_NAME]


async def connect_to_mongo():
    db.client = AsyncIOMotorClient(settings.MONGODB_URL)


async def close_mongo_connection():
    if db.client:
        db.client.close()