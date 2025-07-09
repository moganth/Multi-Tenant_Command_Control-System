from celery_tasks import process_device_telemetry_task, process_device_alert_task

process_device_telemetry_task.delay(
    tenant_id="686e36968f39ae9a1c0710d3",
    device_id="686e3b098f39ae9a1c0710d8",
    telemetry_data={
        "timestamp": "2025-07-09T16:30:00Z",
        "metrics": {
            "temperature": 85,
            "humidity": 40
        },
        "data": {
            "battery": "80%",
            "cpu_usage": 25
        }
    }
)