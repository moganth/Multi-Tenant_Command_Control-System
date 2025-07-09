import subprocess
import sys
import os
import uvicorn

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from config import settings
from utils.database import connect_to_mongo, close_mongo_connection
from utils.mqtt_client import mqtt_client
from utils.supabase_client import supabase_client
from routes import auth, devices, tenants, analytics, commands, health, mqtt
from handlers.auth_handler import get_current_active_user


@asynccontextmanager
async def lifespan(app: FastAPI):

    logger.info("Starting up Multi-Tenant Command & Control System")

    await connect_to_mongo()
    logger.info("Connected to MongoDB")

    supabase_connected = await supabase_client.test_connection()
    if supabase_connected:
        logger.info("Connected to Supabase")
    else:
        logger.error("Failed to connect to Supabase")

    mqtt_client.connect()
    logger.info("Connected to MQTT broker")

    yield

    logger.info("Shutting down Multi-Tenant Command & Control System")

    mqtt_client.disconnect()
    logger.info("Disconnected from MQTT broker")

    await close_mongo_connection()
    logger.info("Disconnected from MongoDB")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="A scalable, cloud-native platform for remote monitoring and control of distributed devices",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["authentication"])
app.include_router(devices.router, prefix=f"{settings.API_V1_STR}/devices", tags=["devices"])
app.include_router(tenants.router, prefix=f"{settings.API_V1_STR}/tenants", tags=["tenants"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])
app.include_router(commands.router, prefix=f"{settings.API_V1_STR}/commands", tags=["commands"])
app.include_router(mqtt.router, prefix=f"{settings.API_V1_STR}/mqtt", tags=["mqtt"])
app.include_router(health.router, prefix=f"{settings.API_V1_STR}/health", tags=["health"])


@app.get("/")
async def root():
    return {
        "message": "Multi-Tenant Command & Control System",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/protected")
async def protected_endpoint(current_user=Depends(get_current_active_user)):
    return {
        "message": "This is a protected endpoint",
        "user": current_user.email,
        "tenant": current_user.tenant_id
    }

def start_celery_worker():
    cmd = [
        sys.executable, "-m", "celery",
        "-A", "celery_app.celery_app",
        "worker",
        "--loglevel=info",
        "--pool=solo"
    ]
    env = os.environ.copy()
    subprocess.Popen(cmd, env=env)


if __name__ == "__main__":
    start_celery_worker()

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )