# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created for Wishlist feature by Elali McNair 3/3/26
# The frontend protion of this code is not finished or implemented yet. Therfore, this code is not oporational or properly implemented yet.

"""
services/wishlist_service.py

Purpose:
This service layer handles business logic for wishlist operations.
It coordinates between controllers and models, adding validation and processing.
"""

from models.wishlist_model import (
    add_to_wishlist,
    get_wishlist_by_user_id,
    remove_from_wishlist,
    is_in_wishlist,
    get_wishlist_item_by_id
)
from models.listing_model import get_listing_by_id


class WishlistService:
    def add_item_to_wishlist(self, user_id, listing_id):
        """
        Adds a listing to user's wishlist.
        Validates the listing exists and is available.
        Returns success status and message.
        """
        # Validate listing exists
        listing = get_listing_by_id(listing_id)
        if not listing:
            return False, "Listing not found"

        # Check if listing is active (allow wishlisting inactive items? For now yes)
        # Users might want to wishlist items that are temporarily out of stock

        try:
            result = add_to_wishlist(user_id, listing_id)
            if result:
                return True, "Item added to wishlist"
            else:
                return False, "Item already in wishlist"
        except Exception as e:
            return False, f"Failed to add item to wishlist: {str(e)}"

    def get_user_wishlist(self, user_id):
        """
        Retrieves the user's wishlist with listing details.
        Returns list of wishlist items.
        """
        try:
            wishlist = get_wishlist_by_user_id(user_id)
            return True, wishlist
        except Exception as e:
            return False, f"Failed to retrieve wishlist: {str(e)}"

    def remove_item_from_wishlist(self, user_id, listing_id):
        """
        Removes a listing from user's wishlist.
        Returns success status and message.
        """
        try:
            removed = remove_from_wishlist(user_id, listing_id)
            if removed:
                return True, "Item removed from wishlist"
            else:
                return False, "Item not found in wishlist"
        except Exception as e:
            return False, f"Failed to remove item from wishlist: {str(e)}"

    def check_item_in_wishlist(self, user_id, listing_id):
        """
        Checks if a specific listing is in user's wishlist.
        Returns boolean status.
        """
        try:
            in_wishlist = is_in_wishlist(user_id, listing_id)
            return True, in_wishlist
        except Exception as e:
            return False, f"Failed to check wishlist status: {str(e)}"

    def get_wishlist_item_details(self, wishlist_id):
        """
        Retrieves detailed information about a specific wishlist item.
        Returns wishlist item details or error.
        """
        try:
            item = get_wishlist_item_by_id(wishlist_id)
            if item:
                return True, item
            else:
                return False, "Wishlist item not found"
        except Exception as e:
            return False, f"Failed to retrieve wishlist item details: {str(e)}"