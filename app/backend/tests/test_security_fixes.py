import io
import os
import re
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest import mock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
for path in (PROJECT_ROOT, BACKEND_ROOT):
    if path not in sys.path:
        sys.path.append(path)

from app import create_app
from db import get_connection
from services.auth_services import AuthService, is_valid_hampton_email
from utils.auth_utils import hash_password

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)

def _run(sql, params=(), fetch=False):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(sql, params)
        row = cur.fetchone() if fetch else None
        conn.commit()
        return row
    finally:
        cur.close()
        conn.close()

class SecurityFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("SECRET_KEY", "unit-test-secret-key-0123456789abcdef")
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        tag = uuid.uuid4().hex[:8]
        cls.tag = tag

        cls.password = "Correct-horse-9"
        cls.username = f"sec_user_{tag}"
        cls.user_id = _run(
            "INSERT INTO users (username, password, email, role) VALUES (%s,%s,%s,'user') RETURNING id;",
            (cls.username, hash_password(cls.password), f"{cls.username}@hamptonu.edu"), fetch=True)[0]
        cls.owner_id = _run(
            "INSERT INTO users (username, password, email, role) VALUES (%s,%s,%s,'user') RETURNING id;",
            (f"sec_owner_{tag}", hash_password(cls.password), f"sec_owner_{tag}@hamptonu.edu"), fetch=True)[0]
        cls.storefront_id = _run(
            "INSERT INTO storefronts (owner_id, brand_name) VALUES (%s,%s) RETURNING id;",
            (cls.owner_id, f"Sec Store {tag}"), fetch=True)[0]
        cls.created_listing_ids = []
        cls.created_files = []

    @classmethod
    def tearDownClass(cls):
        for lid in cls.created_listing_ids:
            _run("DELETE FROM order_items WHERE listing_id = %s;", (lid,))
        _run("DELETE FROM orders WHERE user_id = %s;", (cls.user_id,))
        _run("DELETE FROM cart_items WHERE user_id = %s;", (cls.user_id,))
        _run("DELETE FROM storefronts WHERE id = %s;", (cls.storefront_id,))
        _run("DELETE FROM users WHERE id IN (%s,%s);", (cls.user_id, cls.owner_id))
        for f in cls.created_files:
            if os.path.exists(f):
                os.remove(f)

    def setUp(self):
        self.client = self.app.test_client()
        _run("DELETE FROM cart_items WHERE user_id = %s;", (self.user_id,))
        _run("DELETE FROM order_items WHERE order_id IN (SELECT id FROM orders WHERE user_id = %s);", (self.user_id,))
        _run("DELETE FROM orders WHERE user_id = %s;", (self.user_id,))

    def _login_session(self, user_id=None, role="user", cart=None):
        uid = user_id or self.user_id
        with self.client.session_transaction() as sess:
            sess.clear()
            sess["user"] = f"sec-user-{uid}"
            sess["user_id"] = uid
            sess["role"] = role
            sess["cart"] = cart or []

    def _make_listing(self, price="20.00", qty=5, status="ACTIVE", sizes=None, made_to_order=False):
        listing_id = _run(
            """INSERT INTO listings (storefront_id, title, price, fulfillment_type, quantity_on_hand, status, is_made_to_order)
               VALUES (%s,%s,%s,'IN_STOCK',%s,%s,%s) RETURNING id;""",
            (self.storefront_id, f"Sec Item {uuid.uuid4().hex[:6]}", price, qty, status, made_to_order), fetch=True)[0]
        for size, q in (sizes or {}).items():
            _run("INSERT INTO listing_sizes (listing_id, size, quantity) VALUES (%s,%s,%s);", (listing_id, size, q))
        self.created_listing_ids.append(listing_id)
        return listing_id

    def _listing_row(self, listing_id):
        return _run("SELECT quantity_on_hand, status, price, title FROM listings WHERE id = %s;", (listing_id,), fetch=True)

    def _buyer(self):
        return {"first_name": "Test", "last_name": "Buyer", "email": "t@hamptonu.edu",
                "contact": "555-1212", "meeting_location": "Library"}

    def _order_count(self):
        return _run("SELECT COUNT(*) FROM orders WHERE user_id = %s;", (self.user_id,), fetch=True)[0]

    def test_debug_session_route_is_gone(self):
        self.assertEqual(self.client.get("/auth/debug/session").status_code, 404)

    def test_identity_headers_are_ignored(self):
        spoof = {"X-User-Id": str(self.owner_id), "X-User-Role": "admin"}
        for url in ("/api/storefronts/me", "/api/wishlist"):
            res = self.client.get(url, headers=spoof)
            self.assertEqual(res.status_code, 401, f"{url}: {res.get_data(as_text=True)}")

    def test_spoofed_headers_cannot_override_session_identity(self):
        self._login_session(self.user_id)
        res = self.client.get("/api/storefronts/me",
                              headers={"X-User-Id": str(self.owner_id), "X-User-Role": "admin"})
        self.assertNotEqual(res.status_code, 200, res.get_data(as_text=True))  # must not return owner's storefront

    def test_listing_creation_requires_login_even_with_headers(self):
        spoof = {"X-User-Id": str(self.owner_id), "X-User-Role": "admin"}
        for url in ("/api/listings/create", f"/api/storefronts/{self.storefront_id}/listings", f"/api/listings/1/images", f"/api/listings/1/sizes"):
            res = self.client.post(url, json={"title": "x"}, headers=spoof)
            self.assertIn(res.status_code, (401, 403), f"{url}: {res.get_data(as_text=True)}")

    def test_cart_price_and_name_come_from_database(self):
        listing_id = self._make_listing(price="20.00", qty=5)
        self._login_session()
        res = self.client.post("/auth/add_to_cart", data={
            "item_id": listing_id, "item_name": "HACKED", "price": "0.01", "quantity": "1"})
        self.assertEqual(res.status_code, 302, res.get_data(as_text=True))
        with self.client.session_transaction() as sess:
            item = sess["cart"][0]
        self.assertEqual(item["price"], 20.0)
        self.assertNotEqual(item["name"], "HACKED")
        db_price = _run("SELECT price FROM cart_items WHERE user_id = %s;", (self.user_id,), fetch=True)[0]
        self.assertEqual(float(db_price), 20.0)

    def test_add_to_cart_rejects_bad_quantity_and_ids(self):
        listing_id = self._make_listing()
        self._login_session()
        for qty in ("0", "-5", "999", "abc", ""):
            res = self.client.post("/auth/add_to_cart", data={"item_id": listing_id, "quantity": qty})
            self.assertIn(res.status_code, (400,), f"quantity {qty!r} -> {res.status_code}")
        res = self.client.post("/auth/add_to_cart", data={"item_id": "999999999", "quantity": "1"})
        self.assertEqual(res.status_code, 404)
        res = self.client.post("/auth/add_to_cart", data={"item_id": "notanumber", "quantity": "1"})
        self.assertEqual(res.status_code, 400)

    def test_add_to_cart_rejects_inactive_and_sold_out(self):
        inactive = self._make_listing(status="INACTIVE")
        sold_out = self._make_listing(qty=0, status="SOLD_OUT")
        self._login_session()
        self.assertEqual(self.client.post("/auth/add_to_cart", data={"item_id": inactive, "quantity": "1"}).status_code, 404)
        self.assertEqual(self.client.post("/auth/add_to_cart", data={"item_id": sold_out, "quantity": "1"}).status_code, 409)

    def test_checkout_requires_login(self):
        self.assertEqual(self.client.post("/api/checkout/complete", json=self._buyer()).status_code, 401)

    def test_confirmation_numbers_are_unpredictable_format(self):
        listing_id = self._make_listing(qty=5)
        self._login_session(cart=[{"id": listing_id, "quantity": 1, "size": None}])
        number = self.client.post("/api/checkout/complete", json=self._buyer()).get_json()["confirmation_number"]
        self.assertRegex(number, r"^VAULT-\d{6}-[A-Z0-9]{6}$")

    def test_email_domain_validation(self):
        for ok in ("a@hamptonu.edu", "A.B-c+1@hamptonu.edu", "x@my.hamptonu.edu"):
            self.assertTrue(is_valid_hampton_email(ok), ok)
        for bad in ("a@evilhamptonu.edu", "a@hamptonu.edu.evil.com", "a@hamptonu.edu\n.evil.com", "@hamptonu.edu",
                    "x@gmail.com", "", None, "a@@hamptonu.edu", "a b@hamptonu.edu"):
            self.assertFalse(is_valid_hampton_email(bad), repr(bad))

    def test_password_and_username_policy(self):
        svc = AuthService()
        ok, msg = svc.register_user("gooduser", "short", "a@hamptonu.edu", None)
        self.assertFalse(ok); self.assertIn("Password", msg)
        ok, msg = svc.register_user("ab", "long-enough-pw", "a@hamptonu.edu", None)
        self.assertFalse(ok); self.assertIn("Username", msg)
        ok, msg = svc.register_user("gooduser", "long-enough-pw", "a@evilhamptonu.edu", None)
        self.assertFalse(ok); self.assertIn("Hampton", msg)

    def test_login_success_sets_hardened_session_cookie(self):
        res = self.client.post("/auth/login", data={"username": self.username, "password": self.password})
        self.assertEqual(res.status_code, 302)
        cookie = res.headers.get("Set-Cookie", "")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess["user_id"], self.user_id)

    def test_failed_logins_do_not_leak_db_connections(self):
        def connections():
            return _run("SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database();", fetch=True)[0]
        before = connections()
        for i in range(8):
            self.client.post("/auth/login", data={"username": f"nobody_{self.tag}_{i}", "password": "x"})
        self.assertLessEqual(connections(), before)

    def test_admin_login_uses_environment_credentials(self):
        with mock.patch.dict(os.environ, {"ADMIN_USERNAME": "unit-admin", "ADMIN_PASSWORD": "Unit-Admin-Pass-1"}):
            bad = self.client.post("/auth/admin-login", data={"username": "unit-admin", "password": "nope"})
            self.assertIn("Invalid Admin Credentials", bad.get_data(as_text=True))
            good = self.client.post("/auth/admin-login", data={"username": "unit-admin", "password": "Unit-Admin-Pass-1"})
            self.assertEqual(good.status_code, 302)
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ADMIN_USERNAME", None); os.environ.pop("ADMIN_PASSWORD", None)
            res = self.client.post("/auth/admin-login", data={"username": "", "password": ""})
            self.assertIn("Invalid Admin Credentials", res.get_data(as_text=True))

    def test_security_headers_present(self):
        res = self.client.get("/auth/login")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "SAMEORIGIN")

    def test_create_pages_require_login(self):
        for url in ("/create-listing", "/create-storefront", "/storefronts/create"):
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302, url)
            self.assertIn("/auth/login", res.headers["Location"])

    def test_app_refuses_placeholder_secret_key_outside_development(self):
        for bad in ("", "CHANGE_ME", "change-me", "dev-secret"):
            with mock.patch.dict(os.environ, {"SECRET_KEY": bad, "FLASK_ENV": "production"}):
                with self.assertRaises(RuntimeError, msg=repr(bad)):
                    create_app()

    def test_upload_route_requires_login(self):
        res = self.client.post("/api/storefronts/upload-image",
                               data={"file": (io.BytesIO(PNG_BYTES), "a.png"), "folder": "listings"},
                               content_type="multipart/form-data")
        self.assertEqual(res.status_code, 401)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_escape_helper_neutralises_markup(self):
        js = open(os.path.join(PROJECT_ROOT, "static", "js", "admin.js"), encoding="utf8").read()
        helper = re.search(r"function escapeHtml\(value\) \{.*?\n\}\n", js, flags=re.S).group(0)
        script = helper + 'console.log(escapeHtml(`<img src=x onerror="alert(1)">\'&`));'
        out = subprocess.run(["node", "-e", script], capture_output=True, text=True).stdout.strip()
        self.assertEqual(out, "&#60;img src=x onerror=&#34;alert(1)&#34;&#62;&#39;&#38;")


if __name__ == "__main__":
    unittest.main()
