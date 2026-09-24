# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created by Day Ekoi - Iteration 3

"""
services/listing_service.py

Purpose:
This file contains system rules + validation logic for listings, listing images,
and size-based inventory.

This file handles:
- Input validation
- Permission checks (only storefront owner or admin can modify)
- Multi-step actions (like setting primary images)
- Calls model functions to run SQL queries

Rules enforced:
- Only storefront owner (or admin) can create/update/delete listings
- IN_STOCK listings must have quantity_on_hand
- PREORDER listings ignore quantity_on_hand
- Auto mark SOLD_OUT when inventory hits 0

Image Notes:
- Images are stored as URLs (typically AWS S3 links) in the database.
- Only owner/admin can add/remove/set primary images.

Size Inventory Notes:
- Size inventory is stored in listing_sizes table.
- Only owner/admin can add/update/delete size quantities.
"""

import json

from models.listing_model import (
    create_listing,
    get_listing_by_id,
    get_listings_by_storefront_id,
    update_listing,
    soft_delete_listing,
    deactivate_listing,
    reactivate_listing,
    restore_deleted_listing,
    deactivate_active_listings_for_storefront,
    restore_listings_after_storefront_reactivation,
    # images
    add_listing_image,
    get_images_for_listing,
    set_primary_image,
    delete_listing_image,
    # sizes
    upsert_listing_size,
    get_sizes_for_listing,
    delete_listing_size
)

from models.storefront_model import get_storefront_by_id

# Updated by Day E - April 22nd
# Listing state rules:
# - ACTIVE / SOLD_OUT: seller-facing live states when storefront is active
# - INACTIVE: manually deactivated listing or temporarily hidden listing
# - DELETED: soft-deleted listing kept for admin tracking
# - storefront_restore_status: remembers ACTIVE/SOLD_OUT when storefront-level deactivation pauses a listing
# - deleted_restore_status: remembers the listing's last recoverable state before soft delete


def is_admin(current_user):
    """Returns True if the user has admin privileges."""
    return current_user is not None and current_user.get("role") == "admin"


def _assert_can_manage_listing(current_user, listing):
    """
    Permission rule:
    Only the listing's storefront owner OR an admin can manage listing data.
    """
    storefront = get_storefront_by_id(listing["storefront_id"])
    if storefront is None:
        raise Exception("Storefront not found for this listing.")

    is_owner = storefront["owner_id"] == current_user["id"]
    if not is_owner and not is_admin(current_user):
        raise Exception("Unauthorized action.")


def _assert_can_manage_storefront(current_user, storefront):
    """
    Permission rule:
    Only the storefront owner OR an admin can manage storefront listings.
    """
    is_owner = storefront["owner_id"] == current_user["id"]
    if not is_owner and not is_admin(current_user):
        raise Exception("Unauthorized action.")


# ________________________________________________________
# LISTING SERVICES
# ________________________________________________________

def create_listing_service(current_user, storefront_id, data):
    """
    Creates a new listing under a storefront.

    Enforces:
    - User must be logged in
    - User must own the storefront OR be admin
    - title, price, fulfillment_type are required
    - fulfillment rules enforced
    """
    if current_user is None:
        raise Exception("Error! Unauthorized User.")

    storefront = get_storefront_by_id(storefront_id)
    if storefront is None:
        raise Exception("Storefront not found.")

    _assert_can_manage_storefront(current_user, storefront)

    title = data.get("title")
    if title is None or str(title).strip() == "":
        raise Exception("title is required.")

    price = data.get("price")
    if price is None:
        raise Exception("price is required.")
    try:
        price = float(price)
    except Exception:
        raise Exception("price must be a number.")
    if price < 0:
        raise Exception("price cannot be negative.")

    fulfillment_type = data.get("fulfillment_type")
    if fulfillment_type not in ["IN_STOCK", "PREORDER"]:
        raise Exception("fulfillment_type must be IN_STOCK or PREORDER.")

    is_made_to_order = bool(data.get("is_made_to_order", False))

    quantity_on_hand = data.get("quantity_on_hand")
    if fulfillment_type == "PREORDER":
        quantity_on_hand = None
    elif is_made_to_order:
        # Made-to-order listings do not require inventory — default to 0 if omitted
        try:
            quantity_on_hand = int(quantity_on_hand) if quantity_on_hand is not None else 0
        except Exception:
            quantity_on_hand = 0
        if quantity_on_hand < 0:
            raise Exception("quantity_on_hand cannot be negative.")
    else:
        if quantity_on_hand is None:
            raise Exception("quantity_on_hand is required for IN_STOCK listings.")
        try:
            quantity_on_hand = int(quantity_on_hand)
        except Exception:
            raise Exception("quantity_on_hand must be an integer.")
        if quantity_on_hand < 0:
            raise Exception("quantity_on_hand cannot be negative.")

    # sizes_available (display/list) can be stored as JSON string
    sizes_available = data.get("sizes_available")
    if sizes_available is not None:
        if isinstance(sizes_available, list):
            sizes_available = json.dumps(sizes_available)
        elif not isinstance(sizes_available, str):
            raise Exception("sizes_available must be a list or string.")

    status = (data.get("status") or "ACTIVE").strip()

    # Auto mark SOLD_OUT if inventory hits zero — never for made-to-order
    if not is_made_to_order and fulfillment_type == "IN_STOCK" and quantity_on_hand == 0:
        status = "SOLD_OUT"

    return create_listing(
        storefront_id=storefront_id,
        title=str(title).strip(),
        description=data.get("description"),
        price=price,
        fulfillment_type=fulfillment_type,
        quantity_on_hand=quantity_on_hand,
        sizes_available=sizes_available,
        status=status,
        is_made_to_order=is_made_to_order
    )


def get_listing_by_id_service(listing_id):
    """
    Retrieves a listing by ID.
    """
    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")
    return listing


def get_listings_for_storefront_service(storefront_id):
    """
    Returns all listings for a given storefront.
    """
    return get_listings_by_storefront_id(storefront_id)


def get_listings_for_storefront_with_options_service(storefront_id, include_deleted=False):
    """
    Returns storefront listings with optional deleted listing inclusion.
    Used by owner-facing management views.
    """
    return get_listings_by_storefront_id(storefront_id, include_deleted=include_deleted)


def update_listing_service(current_user, listing_id, data):
    """
    Updates an existing listing.

    Enforces:
    - Only owner/admin can update
    - Fulfillment rules are rechecked if modified
    """
    if current_user is None:
        raise Exception("Error! Unauthorized User.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    _assert_can_manage_listing(current_user, listing)

    fulfillment_type = data.get("fulfillment_type", listing["fulfillment_type"])
    if fulfillment_type not in ["IN_STOCK", "PREORDER"]:
        raise Exception("fulfillment_type must be IN_STOCK or PREORDER.")

    is_made_to_order = None
    if "is_made_to_order" in data:
        is_made_to_order = bool(data["is_made_to_order"])

    effective_mto = is_made_to_order if is_made_to_order is not None else listing.get("is_made_to_order", False)

    quantity_on_hand = data.get("quantity_on_hand", listing["quantity_on_hand"])
    if fulfillment_type == "PREORDER":
        quantity_on_hand = None
    elif effective_mto:
        try:
            quantity_on_hand = int(quantity_on_hand) if quantity_on_hand is not None else 0
        except Exception:
            quantity_on_hand = 0
        if quantity_on_hand < 0:
            raise Exception("quantity_on_hand cannot be negative.")
    else:
        if quantity_on_hand is None:
            raise Exception("quantity_on_hand is required for IN_STOCK listings.")
        try:
            quantity_on_hand = int(quantity_on_hand)
        except Exception:
            raise Exception("quantity_on_hand must be an integer.")
        if quantity_on_hand < 0:
            raise Exception("quantity_on_hand cannot be negative.")

    sizes_available = None
    if "sizes_available" in data:
        sizes_available = data.get("sizes_available")
        if isinstance(sizes_available, list):
            sizes_available = json.dumps(sizes_available)
        elif sizes_available is not None and not isinstance(sizes_available, str):
            raise Exception("sizes_available must be a list or string.")

    title = data.get("title")
    if title is not None:
        title = str(title).strip()
        if title == "":
            raise Exception("title cannot be empty.")

    price = data.get("price")
    if price is not None:
        try:
            price = float(price)
        except Exception:
            raise Exception("price must be a number.")
        if price < 0:
            raise Exception("price cannot be negative.")

    status = data.get("status")
    if status is not None:
        status = str(status).strip()

    if status is None and not effective_mto and fulfillment_type == "IN_STOCK" and quantity_on_hand == 0:
        status = "SOLD_OUT"

    return update_listing(
        listing_id=listing_id,
        title=title if title is not None else None,
        description=data.get("description"),
        price=price,
        fulfillment_type=fulfillment_type,
        quantity_on_hand=quantity_on_hand,
        sizes_available=sizes_available,
        status=status,
        is_made_to_order=is_made_to_order
    )


def delete_listing_service(current_user, listing_id):
    """
    Soft deletes a listing (status = 'DELETED').
    """
    if current_user is None:
        raise Exception("Error! Unauthorized User.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    _assert_can_manage_listing(current_user, listing)

    return soft_delete_listing(listing_id)


def deactivate_listing_service(current_user, listing_id):
    """
    Deactivates a listing without deleting it.
    """
    if current_user is None:
        raise Exception("Error! Unauthorized User.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    if listing["status"] == "DELETED":
        raise Exception("Deleted listings cannot be deactivated.")

    _assert_can_manage_listing(current_user, listing)
    return deactivate_listing(listing_id)


def _get_live_reactivation_status(listing):
    if listing.get("fulfillment_type") == "IN_STOCK" and int(listing.get("quantity_on_hand") or 0) == 0:
        return "SOLD_OUT"
    return "ACTIVE"


def reactivate_listing_service(current_user, listing_id):
    """
    Reactivates a manually deactivated listing.
    Blocked if the parent storefront is currently deactivated.
    """
    if current_user is None:
        raise Exception("Error! Unauthorized User.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    _assert_can_manage_listing(current_user, listing)

    storefront = get_storefront_by_id(listing["storefront_id"])
    if storefront is None:
        raise Exception("Storefront not found.")
    if storefront.get("is_active") is False:
        raise Exception("Reactivate the storefront before reactivating this listing.")
    if listing["status"] == "DELETED":
        raise Exception("Deleted listings cannot be reactivated. Restore the listing instead.")

    live_status = _get_live_reactivation_status(listing)
    return reactivate_listing(listing_id, live_status)


def restore_deleted_listing_service(current_user, listing_id):
    """
    Restores a soft-deleted listing while preserving active vs inactive state.
    """
    if current_user is None:
        raise Exception("Error! Unauthorized User.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    _assert_can_manage_listing(current_user, listing)

    if listing["status"] != "DELETED":
        raise Exception("Only deleted listings can be restored.")

    restored_status = listing.get("deleted_restore_status") or _get_live_reactivation_status(listing)
    storefront = get_storefront_by_id(listing["storefront_id"])
    if storefront is None:
        raise Exception("Storefront not found.")

    storefront_restore_status = None
    if storefront.get("is_active") is False and restored_status in ("ACTIVE", "SOLD_OUT"):
        storefront_restore_status = restored_status
        restored_status = "INACTIVE"

    return restore_deleted_listing(
        listing_id,
        restored_status,
        storefront_restore_status=storefront_restore_status
    )


def deactivate_storefront_listings_service(storefront_id):
    """
    Temporarily inactivates only the listings that were live before storefront shutdown.
    """
    return deactivate_active_listings_for_storefront(storefront_id)


def restore_storefront_listings_service(storefront_id):
    """
    Restores only the listings that storefront-level deactivation inactivated.
    """
    return restore_listings_after_storefront_reactivation(storefront_id)


# ________________________________________________________
# LISTING IMAGE SERVICES
# ________________________________________________________

def add_listing_image_service(current_user, listing_id, image_url, is_primary=False):
    """
    Adds an image to a listing.
    """
    if current_user is None:
        raise Exception("Unauthorized.")

    if image_url is None or str(image_url).strip() == "":
        raise Exception("image_url is required.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    _assert_can_manage_listing(current_user, listing)

    # Updated by Day E - April 22nd
    # Keep listing image management aligned with the create flow: max 4 images total.
    existing_images = get_images_for_listing(listing_id)
    if len(existing_images) >= 4:
        raise Exception("You can upload up to 4 listing images.")

    return add_listing_image(
        listing_id=listing_id,
        image_url=str(image_url).strip(),
        is_primary=bool(is_primary)
    )


def get_listing_images_service(listing_id):
    """
    Public read: returns all images for a listing.
    """
    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")
    return get_images_for_listing(listing_id)


def set_primary_image_service(current_user, listing_id, image_id):
    """
    Sets the primary image for a listing.
    """
    if current_user is None:
        raise Exception("Unauthorized.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    _assert_can_manage_listing(current_user, listing)

    updated = set_primary_image(listing_id, image_id)
    if updated is None:
        raise Exception("Image not found for this listing.")

    return updated


def delete_listing_image_service(current_user, listing_id, image_id):
    """
    Deletes an image record for a listing.
    """
    if current_user is None:
        raise Exception("Unauthorized.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    _assert_can_manage_listing(current_user, listing)

    deleted = delete_listing_image(image_id)
    if not deleted:
        raise Exception("Image not found.")

    return {"deleted": True, "image_id": image_id}


# ________________________________________________________
# LISTING SIZE SERVICES
# ________________________________________________________

def upsert_listing_size_service(current_user, listing_id, size, quantity):
    """
    Creates or updates a size inventory row.
    """
    if current_user is None:
        raise Exception("Unauthorized.")

    if size is None or str(size).strip() == "":
        raise Exception("size is required.")

    try:
        quantity = int(quantity)
    except Exception:
        raise Exception("quantity must be an integer.")

    if quantity < 0:
        raise Exception("quantity cannot be negative.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    _assert_can_manage_listing(current_user, listing)

    return upsert_listing_size(
        listing_id=listing_id,
        size=str(size).strip(),
        quantity=quantity
    )


def get_listing_sizes_service(listing_id):
    """
    Public read: returns all size inventory rows for a listing.
    """
    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")
    return get_sizes_for_listing(listing_id)


def delete_listing_size_service(current_user, listing_id, size):
    """
    Deletes a size inventory row for a listing.
    """
    if current_user is None:
        raise Exception("Unauthorized.")

    if size is None or str(size).strip() == "":
        raise Exception("size is required.")

    listing = get_listing_by_id(listing_id)
    if listing is None:
        raise Exception("Listing not found.")

    _assert_can_manage_listing(current_user, listing)

    deleted = delete_listing_size(listing_id, str(size).strip())
    if not deleted:
        raise Exception("Size row not found.")

    return {"deleted": True, "listing_id": listing_id, "size": str(size).strip()}
