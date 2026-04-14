import mimetypes
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path

from config import (
    EMAIL_FROM,
    EMAIL_HOST,
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_USE_SSL,
    EMAIL_USE_TLS,
    EMAIL_USER,
)


def send_certificate_email(
    to_email: str,
    student_name: str,
    subject: str,
    body: str,
    attachment_path: str,
) -> None:
    if not to_email:
        raise ValueError("Recipient email is required.")

    if not EMAIL_FROM:
        raise ValueError("Email sender is not configured.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = formataddr(("ABC Certificate Verification System", EMAIL_FROM))
    message["To"] = to_email
    message.set_content(body)

    attachment_file = Path(attachment_path)
    if not attachment_file.exists():
        raise FileNotFoundError(f"Attachment not found: {attachment_file}")

    content_type, _ = mimetypes.guess_type(str(attachment_file))
    if content_type is None:
        content_type = "application/octet-stream"
    maintype, subtype = content_type.split("/", 1)

    with attachment_file.open("rb") as attachment:
        message.add_attachment(
            attachment.read(),
            maintype=maintype,
            subtype=subtype,
            filename=attachment_file.name,
        )

    if EMAIL_USE_SSL:
        server_cls = smtplib.SMTP_SSL
    else:
        server_cls = smtplib.SMTP

    with server_cls(EMAIL_HOST, EMAIL_PORT, timeout=20) as server:
        server.ehlo()
        if not EMAIL_USE_SSL and EMAIL_USE_TLS:
            server.starttls()
            server.ehlo()
        if EMAIL_USER and EMAIL_PASSWORD:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(message)
