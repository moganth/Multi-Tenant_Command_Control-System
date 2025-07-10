import paho.mqtt.client as mqtt
import json

from loguru import logger

from config import settings

class MQTTClient:
    def __init__(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.message_handlers = {}

    def on_connect(self, client, userdata, flags, rc):
        logger.info(f"Connected to MQTT broker with result code {rc}")
        # Subscribe to all tenant topics for device status and telemetry
        self.client.subscribe("tenant/+/device/+/status")
        self.client.subscribe("tenant/+/device/+/telemetry")
        self.client.subscribe("tenant/+/device/+/response")
        self.client.subscribe("tenant/+/device/+/alert")
        self.client.subscribe("tenant/+/device/+/heartbeat")
        self.client.subscribe("tenant /+/ device /+/analytics")
        logger.info("Subscribed to all device topics")

    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())

            logger.info(f"Received MQTT message on topic: {topic}")
            logger.debug(f"Payload: {payload}")

            # Extract tenant_id and device_id from topic
            topic_parts = topic.split('/')
            if len(topic_parts) >= 4 and topic_parts[0] == 'tenant':
                tenant_id = topic_parts[1]
                device_id = topic_parts[3]
                message_type = topic_parts[4] if len(topic_parts) > 4 else 'unknown'

                # Route messages to appropriate handlers
                if message_type == 'status':
                    self.handle_device_status(tenant_id, device_id, payload)
                elif message_type == 'telemetry':
                    self.handle_device_telemetry(tenant_id, device_id, payload)
                elif message_type == 'response':
                    self.handle_command_response(tenant_id, device_id, payload)
                elif message_type == 'alert':
                    self.handle_device_alert(tenant_id, device_id, payload)
                elif message_type == 'heartbeat':
                    self.handle_device_heartbeat(tenant_id, device_id, payload)
                else:
                    logger.warning(f"Unknown message type: {message_type}")

        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def on_disconnect(self, client, userdata, rc):
        logger.info(f"Disconnected from MQTT broker with result code {rc}")

    def connect(self):
        if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
            self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

        self.client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def publish(self, topic: str, payload: dict):
        """Publish message to MQTT topic"""
        message = json.dumps(payload)
        result = self.client.publish(topic, message)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            logger.debug(f"Published to {topic}: {message}")
        else:
            logger.error(f"Failed to publish to {topic}: {result.rc}")

    def subscribe(self, topic: str):
        """Subscribe to MQTT topic"""
        self.client.subscribe(topic)
        logger.info(f"Subscribed to topic: {topic}")

    def handle_device_status(self, tenant_id: str, device_id: str, payload: dict):
        """Handle device status messages by triggering Celery tasks"""
        logger.info(f"Handling device status for {tenant_id}/{device_id}")

        # Import here to avoid circular imports
        from celery_tasks import update_device_status_task

        # Trigger Celery task for device status update
        update_device_status_task.delay(tenant_id, device_id, payload)

    def handle_device_telemetry(self, tenant_id: str, device_id: str, payload: dict):
        """Handle device telemetry data by triggering analytics tasks"""
        logger.info(f"Handling telemetry data for {tenant_id}/{device_id}")

        # Import here to avoid circular imports
        from celery_tasks import process_device_telemetry_task

        # Trigger Celery task for telemetry processing
        process_device_telemetry_task.delay(tenant_id, device_id, payload)

    def handle_command_response(self, tenant_id: str, device_id: str, payload: dict):
        """Handle command response messages"""
        logger.info(f"Handling command response for {tenant_id}/{device_id}")

        # Import here to avoid circular imports
        from celery_tasks import update_command_status_task

        # Trigger Celery task for command status update
        update_command_status_task.delay(tenant_id, device_id, payload)

    def handle_device_alert(self, tenant_id: str, device_id: str, payload: dict):
        """Handle device alert messages"""
        logger.info(f"Handling device alert for {tenant_id}/{device_id}")

        # Import here to avoid circular imports
        from celery_tasks import process_device_alert_task

        # Trigger Celery task for alert processing
        process_device_alert_task.delay(tenant_id, device_id, payload)

    def handle_device_heartbeat(self, tenant_id: str, device_id: str, payload: dict):
        """Handle device heartbeat messages"""
        logger.debug(f"Handling heartbeat for {tenant_id}/{device_id}")

        # Import here to avoid circular imports
        from celery_tasks import update_device_heartbeat_task

        # Trigger Celery task for heartbeat update
        update_device_heartbeat_task.delay(tenant_id, device_id, payload)


mqtt_client = MQTTClient()