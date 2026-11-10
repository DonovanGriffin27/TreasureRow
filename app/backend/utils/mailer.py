# Sends email through SMTP (team Gmail account) - Donovan Griffin, Iteration 4
#
# Settings come from .env (see .env.example):
#   MAIL_SERVER, MAIL_PORT, MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM
# If MAIL_SERVER is blank the email is printed to the terminal instead of sent,
# so the app (and the test suite) works without a mail account.

import os
import smtplib
from email.message import EmailMessage


def mail_configured():
    return bool(os.getenv("MAIL_SERVER", "").strip())


def send_email(to, subject, html, text):
    """Send one email. Returns True if it was sent (or printed), False on error."""
    if not mail_configured():
        print(f"[mailer] MAIL_SERVER not set - email not sent.\n  To: {to}\n  Subject: {subject}\n{text}", flush=True)
        return True

    username = os.getenv("MAIL_USERNAME", "")
    if not username or not os.getenv("MAIL_PASSWORD"):
        print(f"[mailer] MAIL_USERNAME or MAIL_PASSWORD is not set - can't send to {to}", flush=True)
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = os.getenv("MAIL_FROM") or username
    msg["To"] = to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")

    try:
        # port 587 + STARTTLS: the connection is encrypted before logging in
        with smtplib.SMTP(os.getenv("MAIL_SERVER"), int(os.getenv("MAIL_PORT", 587)), timeout=10) as smtp:
            smtp.starttls()
            smtp.login(username, os.getenv("MAIL_PASSWORD", ""))
            smtp.send_message(msg)
        print(f"[mailer] Sent '{subject}' to {to}", flush=True)
        return True
    except Exception as e:
        # never let a mail problem crash the page; the error goes to the server log
        print(f"[mailer] Could not send email to {to}: {e}", flush=True)
        return False
