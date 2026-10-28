import io
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
from db import get_connection
from helpers import create_seller, delete_users, png_bytes, sign_in


class TestCreateListingFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        seller = cls._seed_test_data()
        cls.storefront_id, cls.user_id = seller["storefront_id"], seller["user_id"]

    @classmethod
    def _seed_test_data(cls):
        # create our own seller in the TEST database instead of borrowing
        # existing rows - updated by Donovan Griffin, Iteration 3
        conn = get_connection()
        cur = conn.cursor()
        seller = create_seller(cur, "listing")
        conn.commit()
        cur.close()
        conn.close()
        cls.username = seller["username"]
        return seller

    @classmethod
    def tearDownClass(cls):
        delete_users([cls.user_id])

    def setUp(self):
        self.created_listing_ids = []
        with self.client.session_transaction() as sess:
            sess.clear()

    def tearDown(self):
        self._cleanup_created_listings()

    def _auth_headers(self):
        # identity comes from the login session now; the API no longer trusts
        # an X-User-Id header - updated by Donovan Griffin, Iteration 3
        sign_in(self.client, {"username": self.username, "user_id": self.user_id})
        return {}

    def _cleanup_created_listings(self):
        if not self.created_listing_ids:
            return

        conn = get_connection()
        if conn is None:
            return

        cur = conn.cursor()
        try:
            cur.execute(
                "DELETE FROM listings WHERE id = ANY(%s);",
                (self.created_listing_ids,),
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def test_create_listing_from_form_success(self):
        unique_title = f"TEST_CREATE_LISTING_{uuid.uuid4().hex[:8]}"

        response = self.client.post(
            "/api/listings/create",
            data={
                "title": unique_title,
                "quantity_on_hand": "5",
                "price": "39.99",
                "fulfillment_type": "IN_STOCK",
                "status": "ACTIVE",
                "sizes_available": '["M", "L"]',
                "listing_image": (io.BytesIO(png_bytes()), "test_listing.png")  # real PNG: uploads are content-checked (Iteration 3),
            },
            headers=self._auth_headers(),
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 201, response.get_data(as_text=True))
        payload = response.get_json()

        self.assertIsNotNone(payload)
        self.assertEqual(payload["title"], unique_title)
        self.assertEqual(payload["storefront_id"], self.storefront_id)
        self.assertEqual(payload["status"], "ACTIVE")
        self.assertEqual(payload["fulfillment_type"], "IN_STOCK")

        listing_id = payload["id"]
        self.created_listing_ids.append(listing_id)

        verify_response = self.client.get(f"/api/storefronts/{self.storefront_id}/listings")
        self.assertEqual(verify_response.status_code, 200)

        listings = verify_response.get_json()
        matched = next((item for item in listings if item["id"] == listing_id), None)
        self.assertIsNotNone(matched)
        self.assertEqual(matched["title"], unique_title)

    def test_create_listing_requires_image_file(self):
        response = self.client.post(
            "/api/listings/create",
            data={
                "title": f"TEST_CREATE_LISTING_{uuid.uuid4().hex[:8]}",
                "quantity_on_hand": "3",
                "price": "25.00",
                "fulfillment_type": "IN_STOCK",
                "status": "ACTIVE",
                "sizes_available": '["S"]',
            },
            headers=self._auth_headers(),
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 400, response.get_data(as_text=True))
        self.assertIn("listing image is required", response.get_data(as_text=True))

    def test_create_listing_requires_authentication(self):
        response = self.client.post(
            f"/api/storefronts/{self.storefront_id}/listings",
            json={
                "title": "Unauthorized Listing",
                "price": 20,
                "fulfillment_type": "IN_STOCK",
                "quantity_on_hand": 2,
            },
        )

        self.assertEqual(response.status_code, 401, response.get_data(as_text=True))
        self.assertIn("sign in", response.get_data(as_text=True).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
