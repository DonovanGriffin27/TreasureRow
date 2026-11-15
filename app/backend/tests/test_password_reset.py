"""Automated tests for the forgot-password and password-reset workflow.

Run from the application root:
    python3 -m pytest backend/tests/test_password_reset.py -v

These tests use the existing conftest.py environment safeguards. Database access
and email delivery are mocked; no real email or database writes are performed.
"""

import pytest
from flask import Flask

from services import password_reset_service as reset_service


# The service and controller import their dependencies directly, so patch the
# names at the point where each module uses them.
from controllers import auth_controller


@pytest.fixture
def app():
    """A small Flask app containing the real authentication routes."""
    test_app = Flask(__name__, template_folder="templates")
    test_app.config.update(
        SECRET_KEY="test-only-password-reset-secret",
        TESTING=True,
    )
    test_app.register_blueprint(auth_controller.auth_bp, url_prefix="/auth")
    return test_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user():
    # password-reset service expects: (id, username, email, password_hash)
    return [42, "test_user", "test@example.com", "old-password-hash"]


def test_TC_FP_01_valid_reset(app, user, monkeypatch):
    """A valid signed token is accepted and the password is updated."""
    stored_user = user
    updated_passwords = []

    monkeypatch.setattr(
        reset_service,
        "get_user_by_id",
        lambda user_id: stored_user if user_id == stored_user[0] else None,
    )

    def save_password(user_id, password_hash):
        assert user_id == stored_user[0]
        stored_user[3] = password_hash
        updated_passwords.append(password_hash)

    monkeypatch.setattr(reset_service, "update_user_password", save_password)

    with app.app_context():
        token = reset_service.make_reset_token(user[0], user[3])
        found_user, error = reset_service.check_reset_token(token)

        assert error is None
        assert found_user == user

        reset_service.reset_password(user[0], "NewSecurePassword123!")

        assert len(updated_passwords) == 1
        assert stored_user[3] != "old-password-hash"
        assert stored_user[3] == updated_passwords[0]


def test_TC_FP_02_expired_token(app, user, monkeypatch):
    """A token older than the configured lifetime is rejected as expired."""
    monkeypatch.setattr(
        reset_service,
        "get_user_by_id",
        lambda user_id: user if user_id == user[0] else None,
    )

    with app.app_context():
        token = reset_service.make_reset_token(user[0], user[3])

        # A negative max age makes a freshly generated token unambiguously
        # expired, without sleeping or depending on wall-clock timing.
        monkeypatch.setattr(reset_service, "RESET_TOKEN_MINUTES", -1)
        found_user, error = reset_service.check_reset_token(token)

    assert found_user is None
    assert error == "expired"


def test_TC_FP_03_reused_token(app, user, monkeypatch):
    """Changing the password invalidates the token that performed the reset."""
    stored_user = user

    monkeypatch.setattr(
        reset_service,
        "get_user_by_id",
        lambda user_id: stored_user if user_id == stored_user[0] else None,
    )

    def save_password(user_id, password_hash):
        assert user_id == stored_user[0]
        stored_user[3] = password_hash

    monkeypatch.setattr(reset_service, "update_user_password", save_password)

    with app.app_context():
        token = reset_service.make_reset_token(user[0], user[3])

        # First use is valid.
        found_user, error = reset_service.check_reset_token(token)
        assert found_user is not None
        assert error is None

        reset_service.reset_password(user[0], "AnotherSecurePassword456!")

        # The token fingerprint still contains the old password hash.
        found_user, error = reset_service.check_reset_token(token)

    assert found_user is None
    assert error == "invalid"


def test_TC_FP_04_unknown_email(app, monkeypatch):
    """An unknown email receives no email, while the route stays non-enumerating."""
    mailer = pytest.MonkeyPatch()
    try:
        mailer.setattr(reset_service, "get_user_by_email", lambda email: None)
        send_email = mailer.setattr(
            reset_service,
            "send_email",
            lambda *args, **kwargs: pytest.fail("No email should be sent for an unknown address"),
        )

        with app.app_context():
            reset_service.send_reset_email("unknown@example.com")
    finally:
        mailer.undo()

    # The public route gives the same redirect/message regardless of whether
    # the email belongs to an account. Stub the service call so this route test
    # does not depend on a database.
    monkeypatch.setattr(auth_controller, "reset_request", lambda email: True)
    monkeypatch.setattr(
        auth_controller,
        "send_reset_email",
        lambda email: None,
    )
    monkeypatch.setattr(auth_controller, "flash", lambda message: None)

    with app.test_client() as test_client:
        response = test_client.post(
            "/auth/forgot-password",
            data={"email": "unknown@example.com"},
        )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


def test_TC_FP_05_mismatched_passwords(app, client, user, monkeypatch):
    """The reset route rejects a password and confirmation that do not match."""
    monkeypatch.setattr(
        auth_controller,
        "check_reset_token",
        lambda token: (user, None),
    )
    monkeypatch.setattr(
        auth_controller,
        "validate_password",
        lambda password: None,
    )
    monkeypatch.setattr(
        auth_controller,
        "render_template",
        lambda template, **context: context,
    )

    response = client.post(
        "/auth/reset-password/test-token",
        data={
            "password": "ValidSecurePassword123!",
            "confirm_password": "DifferentSecurePassword456!",
        },
    )

    assert response.status_code == 400
    assert response.get_data(as_text=True).find("Passwords don't match") != -1
