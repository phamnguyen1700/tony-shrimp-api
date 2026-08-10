import json
from typing import Any

from app.core.redis import redis_client

NOTIFICATIONS_CHANNEL = "notifications"


async def publish_notification(payload: dict[str, Any]) -> None:
    await redis_client.publish(NOTIFICATIONS_CHANNEL, json.dumps(payload))
