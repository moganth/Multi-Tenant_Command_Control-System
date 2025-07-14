import logging
import time

from celery import Celery
from celery.signals import worker_process_init
from config import settings
from utils.mqtt_client import mqtt_client

celery_app = Celery(
    "mt_command_control",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["celery_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=60,  # 1 minute
)

@worker_process_init.connect
def init_worker_mqtt(**_):
    max_attempts = 10
    attempt = 1
    delay = 5  # seconds

    while attempt <= max_attempts:
        try:
            logging.info(f"[MQTT] Attempt {attempt}: Connecting to {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
            mqtt_client.connect()
            logging.info("[MQTT] Connected successfully.")
            break
        except Exception as e:
            logging.error(f"[MQTT] Connection attempt {attempt} failed: {e}")
            attempt += 1
            time.sleep(delay)
            delay = min(delay * 2, 60)  # exponential backoff (max 60s)

    if attempt > max_attempts:
        logging.critical("[MQTT] Failed to connect after multiple attempts. Exiting.")
