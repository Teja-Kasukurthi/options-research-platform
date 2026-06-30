"""Email notifications via aiosmtplib."""

import structlog
from aiosmtplib import SMTP

from app.core.config import settings

logger = structlog.get_logger(__name__)


async def send_email(subject: str, body: str, to: str | None = None) -> bool:
    smtp_host = getattr(settings, "smtp_host", None)
    smtp_user = getattr(settings, "smtp_user", None)
    smtp_pass = getattr(settings, "smtp_password", None)
    smtp_port = getattr(settings, "smtp_port", 587)

    if not smtp_host:
        logger.debug("smtp_not_configured")
        return False

    recipient = to or settings.admin_email

    from email.mime.text import MIMEText
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = smtp_user or "noreply@options-research"
    msg["To"] = recipient

    try:
        async with SMTP(hostname=smtp_host, port=smtp_port, use_tls=False) as smtp:
            await smtp.ehlo()
            await smtp.starttls()
            if smtp_user and smtp_pass:
                await smtp.login(smtp_user, smtp_pass)
            await smtp.send_message(msg)
        return True
    except Exception as e:
        logger.error("email_send_error", error=str(e))
        return False
