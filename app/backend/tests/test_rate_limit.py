import os
import pytest

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-for-rate-limit-tests")

from app import create_app
from controllers import auth_controller
from utils import rate_limit


class FakeConnect:
    def close(self):
        pass

@pytest.fixture
def client(monkeypatch):
    rate_limit.reset_all()
    app = create_app()
    app.config.update(TESTING=True)
    monkeypatch.setattr(auth_controller, "get_connection", lambda:  FakeConnect())  
    monkeypatch.setattr(auth_controller.service, "validate_login", lambda u, p, c: (False, None))
    yield app.test_client()
    rate_limit.reset_all()

def test_login_lockout_after_5(client):
    for _ in range(5):
        response = client.post("/auth/login", data={"username": "someone", "password": "wrong"})
        assert response.status_code == 401
    # After 5 failed attempts, the user should be locked out
    response = client.post("/auth/login", data={"username": "someone", "password": "wrong"})
    assert response.status_code == 429
    assert b"Too many failed login attempts" in response.data

def test_forgot_password(client, monkeypatch):
    sent = []
    monkeypatch.setattr(auth_controller, "send_reset_email", lambda email: sent.append(email))
    for _ in range(5):
       response = client.post("/auth/forgot-password", data={"email": "student@my.hamptonu.edu"})
       assert response.status_code == 302
    assert len(sent) == 3  # Only 3 requests should be sent
    client.post("/auth/forgot-password", data={"email": "other@my.hamptonu.edu"})
    assert len(sent) == 4  # Different email should be allowed

def test_login_without_username_does_not_crash(client):
    # a login form posted with no username field used to raise a 500 error
    response = client.post("/auth/login", data={"password": "wrong"})
    assert response.status_code == 401
