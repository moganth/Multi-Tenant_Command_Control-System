from celery_tasks import process_device_telemetry_task, process_device_alert_task

process_device_telemetry_task.delay(
    tenant_id="686f68468c3b8b04c45f5a04",
    device_id="686f69bd8c3b8b04c45f5a07",
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