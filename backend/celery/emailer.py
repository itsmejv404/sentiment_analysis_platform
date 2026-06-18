import smtplib
from email.mime.text import MIMEText
from backend import config

# SMTP settings
SMTP_SERVER = config.SMTP_SERVER
SMTP_PORT = config.SMTP_PORT
DEFAULT_FROM_EMAIL = config.DEFAULT_FROM_EMAIL


def send_email(to, subject, body, from_email=DEFAULT_FROM_EMAIL):
    """Sends an email using MailHog SMTP server."""

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to

    try:
        print(f"[EMAIL] Connecting to {SMTP_SERVER}:{SMTP_PORT}")

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)

        server.ehlo()
        server.set_debuglevel(1)
        server.send_message(msg)
        server.quit()
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] Failed to send email: {e}")
        return False