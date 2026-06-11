"""
Emailer — draft and send application emails with PDF attachments.

If SMTP credentials are in .env → sends directly.
If not → saves a .eml draft file Sophie can open in any mail client.
"""

import os
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


SENDER = "sophie.patras@coleurope.eu"

# Default SMTP for Office 365 / Outlook (coleurope.eu runs on M365)
DEFAULT_SMTP_HOST = "smtp.office365.com"
DEFAULT_SMTP_PORT = 587


def _smtp_config() -> dict | None:
    """Return SMTP config from env, or None if not configured."""
    password = os.environ.get("SMTP_PASSWORD")
    if not password:
        return None
    return {
        "host":     os.environ.get("SMTP_HOST",     DEFAULT_SMTP_HOST),
        "port":     int(os.environ.get("SMTP_PORT", DEFAULT_SMTP_PORT)),
        "user":     os.environ.get("SMTP_USER",     SENDER),
        "password": password,
    }


def build_message(
    to: str,
    subject: str,
    body: str,
    cv_pdf: Path,
    cover_letter_pdf: Path,
) -> MIMEMultipart:
    """Assemble the full MIME email with both PDFs attached."""
    msg = MIMEMultipart()
    msg["From"]    = SENDER
    msg["To"]      = to
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain", "utf-8"))

    for pdf_path in (cv_pdf, cover_letter_pdf):
        with open(pdf_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f'attachment; filename="{pdf_path.name}"',
        )
        msg.attach(part)

    return msg


def send(msg: MIMEMultipart) -> bool:
    """
    Send the email via SMTP.
    Returns True on success, False if credentials are missing.
    Raises on network / auth errors so the caller can handle them.
    """
    cfg = _smtp_config()
    if not cfg:
        return False

    context = ssl.create_default_context()
    with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(cfg["user"], cfg["password"])
        server.send_message(msg)

    return True


def save_eml(msg: MIMEMultipart, out_dir: Path) -> Path:
    """Save the message as a .eml file Sophie can open and send manually."""
    eml_path = out_dir / "draft_email.eml"
    eml_path.write_bytes(msg.as_bytes())
    return eml_path
