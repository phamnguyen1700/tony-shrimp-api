from app.core.config import get_settings
from app.services.email.providers.resend import send_email_with_resend

settings = get_settings()


async def send_otp_email(
    *,
    to_email: str,
    code: str,
) -> None:
    subject = "Your Tony Shrimp login code"
    text = f"Your Tony Shrimp login code is {code}."
    html = f"""
    <p>Your Tony Shrimp login code is:</p>
    <p><strong>{code}</strong></p>
    <p>This code will expire in {settings.otp_expire_minutes} minutes.</p>
    """

    if settings.email_provider == "dev":
        print(f"[DEV OTP EMAIL] {to_email}: {code}")
        return

    if settings.email_provider == "resend":
        await send_email_with_resend(
            to_email=to_email,
            subject=subject,
            html=html,
            text=text,
        )
        return

    raise ValueError(f"Unsupported EMAIL_PROVIDER: {settings.email_provider}")
