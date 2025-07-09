from celery_tasks import process_device_alert_task
from datetime import datetime, UTC


process_device_alert_task.delay(
    tenant_id="686e36968f39ae9a1c0710d3",
    device_id="686e3b098f39ae9a1c0710d8",
    alert_data={
        "type": "temperature_high",
        "severity": "critical",
        "message": "Temperature exceeded safe limit",
        "details": {
            "threshold": 85,
            "current": 92
        },
        "timestamp": datetime.now(UTC).isoformat()
    }
)
