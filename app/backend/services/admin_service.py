"""
Admin service helpers for dashboard data and moderation actions.
"""

from models.admin_model import (
    get_all_users,
    delete_user,
    get_all_listings,
    delete_listing,
    get_admin_storefronts,
    delete_storefront,
    get_admin_returns,
    update_admin_return_status,
)


def fetch_users():
    return get_all_users()


def remove_user(user_id):
    if not user_id:
        raise ValueError("User ID required")
    delete_user(user_id)
    return {"message": "User deleted successfully"}


def fetch_listings():
    return get_all_listings()


def remove_listing(listing_id):
    if not listing_id:
        raise ValueError("Listing ID required")
    delete_listing(listing_id)
    return {"message": "Listing soft-deleted successfully"}


def fetch_storefronts():
    return get_admin_storefronts()


def remove_storefront(store_id):
    """
    Deletes a storefront from the system.

    Parameters:
        store_id (int): Storefront identifier

    Returns:
        dict: Success message
    """

    # Basic validation to ensure a storefront ID is provided
    if not store_id:
        raise ValueError("Storefront ID required")

    # Call the model to delete the storefront
    delete_storefront(store_id)

    return {"message": "Storefront removed successfully"}


def fetch_returns():
    return get_admin_returns()


def update_return_status_service(return_id, status):
    if not return_id:
        raise ValueError("Return ID required")
    updated = update_admin_return_status(return_id, status)
    if updated is None:
        raise ValueError("Return not found")
    return updated