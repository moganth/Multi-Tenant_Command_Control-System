import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
from config import settings

# MQTT Configuration
MQTT_BROKER = settings.MQTT_BROKER_HOST
MQTT_PORT = settings.MQTT_BROKER_PORT
MQTT_USERNAME = settings.MQTT_USERNAME
MQTT_PASSWORD = settings.MQTT_PASSWORD  # Set if required

# Device simulation parameters
TENANT_ID = "tenant_123"
DEVICE_ID = "device_456"


def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    # Subscribe to commands for this device
    command_topic = f"tenant/{TENANT_ID}/device/{DEVICE_ID}/command"
    client.subscribe(command_topic)
    print(f"Subscribed to: {command_topic}")


def on_message(client, userdata, msg):
    print(f"Received message on topic: {msg.topic}")
    try:
        payload = json.loads(msg.payload.decode())
        print(f"Command received: {payload}")

        # Simulate command processing
        command_id = payload.get("command_id")
        command = payload.get("command")

        # Send response back
        response_topic = f"tenant/{TENANT_ID}/device/{DEVICE_ID}/response"
        response_payload = {
            "command_id": command_id,
            "status": "completed",
            "result": {"message": f"Command '{command}' executed successfully"},
            "timestamp": datetime.utcnow().isoformat()
        }

        client.publish(response_topic, json.dumps(response_payload))
        print(f"Sent response: {response_payload}")

    except json.JSONDecodeError:
        print("Failed to decode message")


def simulate_device_status(client):
    """Simulate device sending status updates"""
    status_topic = f"tenant/{TENANT_ID}/device/{DEVICE_ID}/status"

    while True:
        status_payload = {
            "status": "online",
            "timestamp": datetime.utcnow().isoformat(),
            "battery_level": 85,
            "signal_strength": -45,
            "temperature": 23.5
        }

        client.publish(status_topic, json.dumps(status_payload))
        print(f"Sent status update: {status_payload}")

        time.sleep(30)  # Send status every 30 seconds


if __name__ == "__main__":
    # Create MQTT client
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    # Set credentials if needed
    if MQTT_USERNAME and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

    # Connect to broker
    client.connect(MQTT_BROKER, MQTT_PORT, 60)

    # Start the loop in a separate thread
    client.loop_start()

    try:
        # Simulate device status updates
        simulate_device_status(client)
    except KeyboardInterrupt:
        print("Stopping device simulation...")
        client.loop_stop()
        client.disconnect()