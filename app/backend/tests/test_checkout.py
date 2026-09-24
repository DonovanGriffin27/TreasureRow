import os
import sys
import unittest
import uuid

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

for path in (PROJECT_ROOT, BACKEND_ROOT):
    if path not in sys.path:
        sys.path.append(path)

from app import create_app
from backend.config.db import get_connection


class TestCheckoutFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        cls.user_id = cls._resolve_test_user()

        if cls.user_id is None:
            raise unittest.SkipTest("No user data available for checkout tests.")

    @staticmethod
    def _resolve_test_user():
        conn = get_connection()
        if conn is None:
            return None

        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT id
                FROM users
                ORDER BY id
                LIMIT 1;
                """
            )
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            cur.close()
            conn.close()

    def setUp(self):
        self.created_cart_item_ids = []
        self.created_order_ids = []

    def tearDown(self):
        self._cleanup_orders()
        self._cleanup_cart_items()

    def _auth_headers(self):
        return {"X-User-Id": str(self.user_id)}

    def _cleanup_cart_items(self):
        if not self.created_cart_item_ids:
            return

        conn = get_connection()
        if conn is None:
            return

        cur = conn.cursor()
        try:
            cur.execute(
                "DELETE FROM cart_items WHERE id = ANY(%s);",
                (self.created_cart_item_ids,),
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def _cleanup_orders(self):
        if not self.created_order_ids:
            return

        conn = get_connection()
        if conn is None:
            return

        cur = conn.cursor()
        try:
            cur.execute(
                "DELETE FROM order_items WHERE order_id = ANY(%s);",
                (self.created_order_ids,),
            )
            cur.execute(
                "DELETE FROM orders WHERE id = ANY(%s);",
                (self.created_order_ids,),
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def _seed_cart_item(self, title=None, price=10.00, quantity=1):
        conn = get_connection()
        if conn is None:
            self.fail("Database connection unavailable.")

        cur = conn.cursor()
        try:
            item_title = title or f"TEST_CHECKOUT_ITEM_{uuid.uuid4().hex[:8]}"
            cur.execute(
                """
                INSERT INTO cart_items (user_id, title, price, quantity)
                VALUES (%s, %s, %s, %s)
                RETURNING id;
                """,
                (self.user_id, item_title, price, quantity),
            )
            row = cur.fetchone()
            conn.commit()

            cart_item_id = row[0]
            self.created_cart_item_ids.append(cart_item_id)
            return cart_item_id
        finally:
            cur.close()
            conn.close()

    def test_checkout_summary_calculates_total_successfully(self):
        self._seed_cart_item(price=15.00, quantity=2)   # 30.00
        self._seed_cart_item(price=5.50, quantity=3)    # 16.50
        expected_total = 46.50

        response = self.client.get(
            "/api/checkout/summary",
            headers=self._auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()

        self.assertIsNotNone(payload)
        self.assertIn("items", payload)
        self.assertIn("total", payload)
        self.assertAlmostEqual(float(payload["total"]), expected_total, places=2)

    def test_checkout_prefills_existing_user_information(self):
        response = self.client.get(
            "/api/checkout/prefill",
            headers=self._auth_headers(),
        )

        self.assertEqual(response.status_code, 200, response.get_data(as_text=True))
        payload = response.get_json()

        self.assertIsNotNone(payload)
        self.assertIn("user_id", payload)
        self.assertEqual(payload["user_id"], self.user_id)

    def test_complete_transaction_creates_order_successfully(self):
        self._seed_cart_item(price=20.00, quantity=2)

        response = self.client.post(
            "/api/checkout/complete",
            json={
                "shipping_info": {
                    "full_name": "Test User",
                    "address_line_1": "123 Test Lane",
                    "city": "Hampton",
                    "state": "VA",
                    "postal_code": "23668",
                },
                "payment_info": {
                    "cardholder_name": "Test User",
                    "card_last4": "4242",
                    "payment_method": "CARD",
                },
            },
            headers=self._auth_headers(),
        )

        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        payload = response.get_json()

        self.assertIsNotNone(payload)
        self.assertIn("order_id", payload)
        self.assertIn("message", payload)

        self.created_order_ids.append(payload["order_id"])

    def test_complete_transaction_requires_authentication(self):
        response = self.client.post(
            "/api/checkout/complete",
            json={
                "shipping_info": {
                    "full_name": "Unauthorized User",
                    "address_line_1": "111 Nowhere St",
                    "city": "Nowhere",
                    "state": "VA",
                    "postal_code": "00000",
                },
                "payment_info": {
                    "cardholder_name": "Unauthorized User",
                    "card_last4": "1111",
                    "payment_method": "CARD",
                },
            },
        )

        self.assertEqual(response.status_code, 401, response.get_data(as_text=True))
        self.assertIn("Unauthorized", response.get_data(as_text=True))

    def test_complete_transaction_rejects_empty_cart(self):
        response = self.client.post(
            "/api/checkout/complete",
            json={
                "shipping_info": {
                    "full_name": "Test User",
                    "address_line_1": "123 Test Lane",
                    "city": "Hampton",
                    "state": "VA",
                    "postal_code": "23668",
                },
                "payment_info": {
                    "cardholder_name": "Test User",
                    "card_last4": "4242",
                    "payment_method": "CARD",
                },
            },
            headers=self._auth_headers(),
        )

        self.assertIn(response.status_code, [400, 409], response.get_data(as_text=True))

    def test_order_confirmation_page_loads_after_successful_checkout(self):
        self._seed_cart_item(price=12.00, quantity=1)

        checkout_response = self.client.post(
            "/api/checkout/complete",
            json={
                "shipping_info": {
                    "full_name": "Test User",
                    "address_line_1": "123 Test Lane",
                    "city": "Hampton",
                    "state": "VA",
                    "postal_code": "23668",
                },
                "payment_info": {
                    "cardholder_name": "Test User",
                    "card_last4": "4242",
                    "payment_method": "CARD",
                },
            },
            headers=self._auth_headers(),
        )

        self.assertEqual(checkout_response.status_code, 201, checkout_response.get_data(as_text=True))
        payload = checkout_response.get_json()

        self.assertIsNotNone(payload)
        order_id = payload["order_id"]
        self.created_order_ids.append(order_id)

        confirmation_response = self.client.get(
            f"/api/orders/{order_id}/confirmation",
            headers=self._auth_headers(),
        )

        self.assertEqual(confirmation_response.status_code, 200, confirmation_response.get_data(as_text=True))

    def test_checkout_summary_requires_authentication(self):
        response = self.client.get("/api/checkout/summary")

        self.assertEqual(response.status_code, 401, response.get_data(as_text=True))
        self.assertIn("Unauthorized", response.get_data(as_text=True))

    def test_checkout_prefill_requires_authentication(self):
        response = self.client.get("/api/checkout/prefill")

        self.assertEqual(response.status_code, 401, response.get_data(as_text=True))
        self.assertIn("Unauthorized", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)