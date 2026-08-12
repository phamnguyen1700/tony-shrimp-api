from app.core.config import get_settings
from app.services.email.providers.resend import send_email_with_resend

settings = get_settings()


def build_otp_email_text(code: str) -> str:
    return (
        f"Your Tony Shrimp login code is {code}.\n\n"
        f"This code will expire in {settings.otp_expire_minutes} minutes.\n"
        "If you did not request this code, you can ignore this email."
    )


def build_otp_email_html(code: str) -> str:
    logo_html = (
        f'<img src="{settings.email_logo_url}" width="42" height="42" alt="Tony Shrimp" '
        'style="display:block;width:42px;height:42px;border:0;outline:none;text-decoration:none;">'
        if settings.email_logo_url
        else '<div style="width:42px;height:42px;border:1px solid #171713;background:#171713;color:#fffdf8;text-align:center;font-family:Georgia,'
        "'Times New Roman',serif;font-size:19px;line-height:42px;font-weight:700;\">TS</div>"
    )

    return f"""\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Your Tony Shrimp login code</title>
  </head>
  <body style="margin:0;background:#f5f2ec;font-family:Arial,Helvetica,sans-serif;color:#171713;">
    <div style="display:none;max-height:0;overflow:hidden;opacity:0;">
      Your Tony Shrimp login code is {code}. It expires in {settings.otp_expire_minutes} minutes.
    </div>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f2ec;padding:32px 16px;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background:#fffdf8;border:1px solid #ded8cc;">
            <tr>
              <td style="padding:24px 32px 20px 32px;border-bottom:1px solid #e5ded2;">
                <table role="presentation" cellspacing="0" cellpadding="0">
                  <tr>
                    <td width="46" valign="middle" style="padding:0 14px 0 0;">
                      {logo_html}
                    </td>
                    <td valign="middle" style="padding:0;text-align:left;">
                      <div style="font-family:Georgia,'Times New Roman',serif;font-size:22px;font-weight:700;letter-spacing:4px;text-transform:uppercase;color:#11110f;">
                        Tony Shrimp
                      </div>
                      <div style="margin-top:4px;font-size:11px;letter-spacing:5px;text-transform:uppercase;color:#6f6a60;">
                        Australia
                      </div>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:34px 32px 10px 32px;">
                <h1 style="margin:0 0 12px 0;font-family:Georgia,'Times New Roman',serif;font-size:28px;line-height:1.2;font-weight:700;color:#11110f;">
                  Your login code
                </h1>
                <p style="margin:0;font-size:15px;line-height:1.7;color:#555047;">
                  Use this one-time code to sign in to your Tony Shrimp account.
                </p>
              </td>
            </tr>
            <tr>
              <td style="padding:18px 32px 24px 32px;">
                <div style="background:#f2eee6;border:1px solid #d8d0c2;padding:22px 16px;text-align:center;">
                  <div style="font-size:34px;line-height:1;font-weight:700;letter-spacing:8px;color:#11110f;">
                    {code}
                  </div>
                </div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 32px 34px 32px;">
                <p style="margin:0 0 10px 0;font-size:14px;line-height:1.7;color:#555047;">
                  This code will expire in <strong>{settings.otp_expire_minutes} minutes</strong>.
                </p>
                <p style="margin:0;font-size:13px;line-height:1.7;color:#777166;">
                  If you did not request this code, you can safely ignore this email.
                </p>
              </td>
            </tr>
          </table>
          <p style="margin:18px 0 0 0;font-size:12px;line-height:1.6;color:#8a8378;">
            Sent by Tony Shrimp Australia
          </p>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


async def send_otp_email(
    *,
    to_email: str,
    code: str,
) -> None:
    subject = "Your Tony Shrimp login code"
    text = build_otp_email_text(code)
    html = build_otp_email_html(code)

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
