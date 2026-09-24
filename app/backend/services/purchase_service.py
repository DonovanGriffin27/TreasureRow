# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created for Purchase History feature by Elali McNair 3/3/26
# The frontend protion of this code is not finished or implemented yet. Therfore, this code is not oporational or properly implemented yet.

"""
services/purchase_service.py

Purpose:
This service layer handles business logic for purchase operations.
It coordinates between controllers and models, adding validation and processing.
"""

from models.purchase_model import (
    create_purchase,
    get_purchases_by_user_id,
    get_purchase_by_id
)
from models.listing_model import get_listing_by_id


class PurchaseService:
    def record_purchase(self, user_id, listing_id, quantity):
        """
        Records a new purchase for a user.
        Validates the listing exists and is available.
        Returns the created purchase or error message.
        """
        # Validate listing exists
        listing = get_listing_by_id(listing_id)
        if not listing:
            return False, "Listing not found"

        # Check if listing is active
        if listing['status'] != 'ACTIVE':
            return False, "Listing is not available for purchase"

        # For now, assume purchase at current price
        # In a real system, this might involve payment processing
        purchase_price = listing['price']

        try:
            purchase = create_purchase(user_id, listing_id, quantity, purchase_price)
            return True, purchase
        except Exception as e:
            return False, f"Failed to record purchase: {str(e)}"

    def get_user_purchase_history(self, user_id):
        """
        Retrieves the complete purchase history for a user.
        Returns list of purchases with listing and storefront details.
        """
        try:
            purchases = get_purchases_by_user_id(user_id)
            return True, purchases
        except Exception as e:
            return False, f"Failed to retrieve purchase history: {str(e)}"

    def get_purchase_details(self, purchase_id):
        """
        Retrieves detailed information about a specific purchase.
        Returns purchase details or error.
        """
        try:
            purchase = get_purchase_by_id(purchase_id)
            if purchase:
                return True, purchase
            else:
                return False, "Purchase not found"
        except Exception as e:
            return False, f"Failed to retrieve purchase details: {str(e)}"