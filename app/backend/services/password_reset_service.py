# Forgot password: reset links and emails - Donovan Griffin, Iteration 4
#
# How a reset link stays safe without a new database table:
#  - The token is signed with the app's SECRET_KEY (itsdangerous), so it can't
#    be forged or edited.
#  - It expires after RESET_TOKEN_MINUTES.
#  - It carries a fingerprint of the user's current password hash. Once the
#    password changes the fingerprint no longer matches, so each link works
#    only once (and older links stop working too).

import hashlib

from flask import current_app, render_template, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from jinja2 import TemplateNotFound
from markupsafe import escape

from models.auth_model import get_user_by_email, get_user_by_id, update_user_password
from utils.auth_utils import hash_password
from utils.mailer import send_email

RESET_TOKEN_MINUTES = 30


def _serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="password-reset")


def _fingerprint(password_hash):
    # a short digest, so the token never contains any part of the real hash
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def make_reset_token(user_id, password_hash):
    return _serializer().dumps({"uid": user_id, "fp": _fingerprint(password_hash)})


def check_reset_token(token):
    """Return (user_row, error). error is "expired" or "invalid" when the link can't be used."""
    try:
        data = _serializer().loads(token, max_age=RESET_TOKEN_MINUTES * 60)
    except SignatureExpired:
        return None, "expired"
    except BadSignature:
        return None, "invalid"

    user = get_user_by_id(data.get("uid"))
    # password already changed since the link was sent -> link was used
    if not user or _fingerprint(user[3]) != data.get("fp"):
        return None, "invalid"
    return user, None


def send_reset_email(email):
    """Email a reset link if the address belongs to an account. Silent otherwise."""
    user = get_user_by_email(email)
    if not user:
        # server log only; the page shows the same message either way
        print(f"[forgot-password] no account has the email {email!r} - nothing sent", flush=True)
        return

    user_id, username, user_email, password_hash = user
    link = url_for("auth.reset_password", token=make_reset_token(user_id, password_hash), _external=True)
    context = {"username": username, "reset_link": link, "expires_minutes": RESET_TOKEN_MINUTES}

    # Cameron's branded templates (templates/emails/) are used once they exist
    try:
        html = render_template("emails/reset_password.html", **context)
        text = render_template("emails/reset_password.txt", **context)
    except TemplateNotFound:
        text = (
            f"Hi {username},\n\n"
            f"Someone asked to reset your Treasure Row password. Use this link within "
            f"{RESET_TOKEN_MINUTES} minutes:\n\n{link}\n\n"
            "If you didn't ask for this, ignore this email - your password won't change."
        )
        html = (
            f"<p>Hi {escape(username)},</p>"
            f"<p>Someone asked to reset your Treasure Row password. Use this link within "
            f"{RESET_TOKEN_MINUTES} minutes:</p>"
            f'<p><a href="{link}">Reset my password</a></p>'
            "<p>If you didn't ask for this, ignore this email - your password won't change.</p>"
        )

    send_email(user_email, "Reset your Treasure Row password", html, text)


def reset_password(user_id, new_password):
    update_user_password(user_id, hash_password(new_password))
