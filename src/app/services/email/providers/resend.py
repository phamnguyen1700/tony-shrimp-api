import httpx

from app.core.config import get_settings

settings = get_settings()


async def send_email_with_resend(
    *,
    to_email: str,
    subject: str,
    html: str,
    text: str | None = None,
) -> None:
    if not settings.resend_api_key:
        raise ValueError("RESEND_API_KEY is required when EMAIL_PROVIDER=resend.")

    payload = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": subject,
        "html": html,
    }

    if text is not None:
        payload["text"] = text

    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(
            settings.resend_api_url,
            json=payload,
            headers=headers,
        )

    response.raise_for_status()
