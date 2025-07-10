from celery_tasks import process_device_alert_task
from datetime import datetime, UTC


process_device_alert_task.delay(
    tenant_id="686f68468c3b8b04c45f5a04",
    device_id="686f69bd8c3b8b04c45f5a07",
    alert_data={
        "type": "temperature_high",
        "severity": "critical",
        "message": "Temperature exceeded safe limit",
        "details": {
            "threshold": 80,
            "current": 120
        },
        "timestamp": datetime.now(UTC).isoformat()
    }
)
