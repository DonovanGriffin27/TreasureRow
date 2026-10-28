import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

for path in (PROJECT_ROOT, BACKEND_ROOT):
    if path not in sys.path:
        sys.path.append(path)

from app import create_app
from db import get_connection
from helpers import create_seller, delete_users, sign_in


class TestWishlistFeature(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()
        seller = cls._seed_test_data()
        cls.user_id, cls.listing_id = seller["user_id"], seller["listing_id"]

    @classmethod
    def _seed_test_data(cls):
        # create our own seller in the TEST database instead of borrowing
        # existing rows - updated by Donovan Griffin, Iteration 3
        conn = get_connection()
        cur = conn.cursor()
        seller = create_seller(cur, "wishlist")
        conn.commit()
        cur.close()
        conn.close()
        cls.username = seller["username"]
        return seller

    @classmethod
    def tearDownClass(cls):
        delete_users([cls.user_id])

    def setUp(self):
        self._cleanup_wishlist_item()
        with self.client.session_transaction() as sess:
            sess.clear()

    def tearDown(self):
        self._cleanup_wishlist_item()

    def _cleanup_wishlist_item(self):
        conn = get_connection()
        if conn is None or self.user_id is None or self.listing_id is None:
            return

        cur = conn.cursor()
        try:
            cur.execute(
                "DELETE FROM wishlist WHERE user_id = %s AND listing_id = %s;",
                (self.user_id, self.listing_id),
            )
            conn.commit()
        finally:
            cur.close()
            conn.close()

    def _auth_headers(self):
        # identity comes from the login session now; the API no longer trusts
        # an X-User-Id header - updated by Donovan Griffin, Iteration 3
        sign_in(self.client, {"username": self.username, "user_id": self.user_id})
        return {}

    def test_add_get_check_and_remove_wishlist_item(self):
        add_response = self.client.post(
            "/api/wishlist",
            json={"listing_id": self.listing_id},
            headers=self._auth_headers(),
        )
        self.assertEqual(add_response.status_code, 201, add_response.get_data(as_text=True))

        check_response = self.client.get(
            f"/api/wishlist/{self.listing_id}/check",
            headers=self._auth_headers(),
        )
        self.assertEqual(check_response.status_code, 200)
        self.assertTrue(check_response.get_json()["in_wishlist"])

        wishlist_response = self.client.get(
            "/api/wishlist",
            headers=self._auth_headers(),
        )
        self.assertEqual(wishlist_response.status_code, 200, wishlist_response.get_data(as_text=True))

        wishlist = wishlist_response.get_json().get("wishlist", [])
        matched_item = next(
            (item for item in wishlist if int(item.get("listing_id", -1)) == self.listing_id),
            None,
        )

        self.assertIsNotNone(matched_item)
        self.assertIn("listing", matched_item)
        self.assertIn("storefront", matched_item)
        self.assertIn("title", matched_item["listing"])
        self.assertIn("price", matched_item["listing"])
        self.assertIn("brand_name", matched_item["storefront"])

        remove_response = self.client.delete(
            f"/api/wishlist/{self.listing_id}",
            headers=self._auth_headers(),
        )
        self.assertEqual(remove_response.status_code, 200, remove_response.get_data(as_text=True))

        final_check_response = self.client.get(
            f"/api/wishlist/{self.listing_id}/check",
            headers=self._auth_headers(),
        )
        self.assertEqual(final_check_response.status_code, 200)
        self.assertFalse(final_check_response.get_json()["in_wishlist"])

    def test_duplicate_add_returns_error(self):
        first_response = self.client.post(
            "/api/wishlist",
            json={"listing_id": self.listing_id},
            headers=self._auth_headers(),
        )
        self.assertEqual(first_response.status_code, 201, first_response.get_data(as_text=True))

        second_response = self.client.post(
            "/api/wishlist",
            json={"listing_id": self.listing_id},
            headers=self._auth_headers(),
        )
        self.assertEqual(second_response.status_code, 400, second_response.get_data(as_text=True))
        self.assertIn("already in wishlist", second_response.get_data(as_text=True).lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
