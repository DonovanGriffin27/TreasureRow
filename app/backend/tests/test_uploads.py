# backend/tests/test_uploads.py
# Created by Donovan Griffin - Iteration 3
#
# Image uploads must only ever store real images, in the app's upload folders.
# Before this fix: the storefront upload's "folder" form value went straight
# into the save path (../../ wrote files anywhere), a web page renamed
# photo.png was accepted, the browser chose the stored Content-Type, and
# there was no size limit. Runs in local-storage mode (see conftest.py).

import io
import os

import pytest

from app import create_app
from db import get_connection
from helpers import create_seller, delete_users, png_bytes, sign_in

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
UPLOAD_DIR = os.path.join(APP_DIR, "static", "uploads")


HTML_AS_PNG = b"<html><script>alert(document.cookie)</script></html>"


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seller():
    conn = get_connection()
    cur = conn.cursor()
    s = create_seller(cur, "upload")
    conn.commit()
    cur.close()
    conn.close()
    yield s
    delete_users([s["user_id"]])


@pytest.fixture
def created_files():
    """Remove any files a test uploads."""
    paths = []
    yield paths
    for p in paths:
        if os.path.exists(p):
            os.remove(p)


def _upload(client, data_bytes, filename="photo.png", folder="storefronts/logos"):
    return client.post(
        "/api/storefronts/upload-image",
        data={"file": (io.BytesIO(data_bytes), filename), "folder": folder},
        content_type="multipart/form-data",
    )


def _local_path(url):
    return os.path.join(APP_DIR, url.lstrip("/"))


def test_real_image_uploads(client, seller, created_files):
    sign_in(client, seller)
    response = _upload(client, png_bytes())
    assert response.status_code == 200, response.get_data(as_text=True)
    url = response.get_json()["url"]
    created_files.append(_local_path(url))
    assert url.startswith("/static/uploads/storefronts/logos/") and url.endswith(".png")
    assert os.path.exists(_local_path(url))


@pytest.mark.parametrize("folder", ["../../templates", "/etc", "storefronts/../../..", "listings/../../static", "anything-else"])
def test_folder_outside_upload_area_is_rejected(client, seller, folder):
    sign_in(client, seller)
    before = set(os.listdir(os.path.join(APP_DIR, "templates")))
    response = _upload(client, png_bytes(), folder=folder)
    assert response.status_code == 400
    assert set(os.listdir(os.path.join(APP_DIR, "templates"))) == before


@pytest.mark.parametrize("payload,filename", [
    (HTML_AS_PNG, "photo.png"),                       # web page renamed .png
    (b"<svg onload=alert(1)></svg>", "photo.svg"),    # svg can carry script
    (b"not an image at all", "photo.jpg"),
])
def test_non_images_are_rejected(client, seller, payload, filename):
    sign_in(client, seller)
    assert _upload(client, payload, filename=filename).status_code == 400


def test_image_over_5mb_is_rejected(client, seller):
    sign_in(client, seller)
    big = png_bytes() + b"\x00" * (5 * 1024 * 1024 + 1)
    assert _upload(client, big).status_code == 400


def test_request_over_25mb_is_refused(client, seller):
    sign_in(client, seller)
    assert _upload(client, b"\x00" * (26 * 1024 * 1024)).status_code == 413


def test_listing_upload_rejects_fake_image(client, seller):
    sign_in(client, seller)
    response = client.post(
        "/api/listings/create",
        data={
            "title": "Fake image listing", "price": "10",
            "sizes_available": '["M"]', "size_quantities": '{"M": 1}',
            "listing_images": (io.BytesIO(HTML_AS_PNG), "photo.png"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_return_upload_rejects_fake_image(client, seller):
    # a real order first, so the request gets past the order-ownership check
    sign_in(client, seller)
    with client.session_transaction() as sess:
        sess["cart"] = [{"id": seller["listing_id"], "quantity": 1, "size": "M"}]
    order = client.post("/api/checkout/complete", json={
        "first_name": "T", "last_name": "B", "email": "t@my.hamptonu.edu",
        "contact": "555", "meeting_location": "Library"}).get_json()
    response = client.post(
        "/returns",
        data={
            "order_number": order["confirmation_number"], "reason": "damaged", "has_damage": "yes",
            "damage_image": (io.BytesIO(HTML_AS_PNG), "damage.png"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "image" in response.get_json()["error"].lower()
