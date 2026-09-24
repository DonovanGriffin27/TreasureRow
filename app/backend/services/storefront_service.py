# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created by Day Ekoi - Iteration 3
# Updated by Day Ekoi - Iteration 5 - 4/10/26 - 4/20/26  - added preview_image_1-4 passthrough in create and update services

"""
storefront_service.py

Purpose: This file enforces rules such as ownership checks, validation, and permissions

What it does:
- checks permissions (owner vs admin)
- Enforces any rules (ex: a user can only have 1 storefront)
- Validates required input (ex: Brand name)
- Calls the model file (storefront_model.py) to run SQL queries

Additionally, this service expects image URLs (S3) to be stored in the DB.
"""

from models.storefront_model import (
    create_storefront,
    get_storefront_by_id,
    get_storefront_by_owner_id,
    update_storefront,
    set_storefront_active
)
from services.listing_service import (
    deactivate_storefront_listings_service,
    restore_storefront_listings_service,
)

MAX_STOREFRONT_CATEGORIES = 3

# Updated by Day E - April 22nd
# Storefront state rules:
# - is_active = TRUE: storefront is public
# - is_active = FALSE: storefront is owner/admin accessible but hidden from public users
# - storefront deactivation pauses only listings that were ACTIVE/SOLD_OUT
# - storefront reactivation restores only listings carrying storefront_restore_status


def is_admin(current_user):
    """
    Returns True if the logged-in user is an admin.
    """
    return current_user.get("role") == "admin"


def normalize_storefront_categories(raw_categories):
    """
    Accepts storefront categories as a comma-delimited string or list,
    trims values, removes duplicates, and enforces the max selection limit.
    """
    if raw_categories is None:
        return None

    if isinstance(raw_categories, str):
        values = [value.strip() for value in raw_categories.split(",")]
    elif isinstance(raw_categories, list):
        values = [str(value).strip() for value in raw_categories]
    else:
        raise Exception("categories must be a string or list.")

    cleaned = []
    seen = set()
    for value in values:
        if not value:
            continue
        normalized_key = value.lower()
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        cleaned.append(value)

    if len(cleaned) > MAX_STOREFRONT_CATEGORIES:
        raise Exception(f"You can select up to {MAX_STOREFRONT_CATEGORIES} storefront categories.")

    return ",".join(cleaned) if cleaned else None


def create_storefront_service(current_user, data):
    """
    Creates a storefront for a current user.

    Rules:
    - user must be logged in
    - user can only create one storefront
    - brand_name is required
    """

    # Rule 1: Must be logged in
    if not current_user:
        raise Exception("Error! Unauthorized user.")

    # Rule 2: Prevent duplicate storefronts
    existing = get_storefront_by_owner_id(current_user["id"])
    if existing:
        raise Exception("Storefront already created.")

    # Rule 3: Validate required input
    brand_name = (data.get("brand_name") or "").strip()
    if not brand_name:
        raise Exception("brand_name is required")

    categories = normalize_storefront_categories(data.get("categories"))

    # Rule 4: Call model to insert into database
    return create_storefront(
        owner_id=current_user["id"],
        brand_name=brand_name,
        bio=data.get("bio"),
        logo_url=data.get("logo_url"),
        banner_url=data.get("banner_url"),
        contact_info=data.get("contact_info"),
        preview_image_1=data.get("preview_image_1"),
        preview_image_2=data.get("preview_image_2"),
        preview_image_3=data.get("preview_image_3"),
        preview_image_4=data.get("preview_image_4"),
        categories=categories,
    )


def get_my_storefront_service(current_user):
    """
    Returns the storefront owned by the current user.
    """
    if not current_user:
        raise Exception("Error! Unauthorized user.")

    return get_storefront_by_owner_id(current_user["id"])


def update_storefront_service(current_user, storefront_id, data):
    """
    Updates an existing storefront.

    Permissions:
    - Owner can update
    - Admin can update any storefront
    """

    if not current_user:
        raise Exception("Error! Unauthorized user.")

    storefront = get_storefront_by_id(storefront_id)
    if not storefront:
        raise Exception("Storefront not found.")

    is_owner = (storefront["owner_id"] == current_user["id"])
    if not is_owner and not is_admin(current_user):
        raise Exception("Unauthorized action.")

    # Only allow safe fields
    allowed_fields = {"brand_name", "bio", "logo_url", "banner_url", "contact_info",
                      "preview_image_1", "preview_image_2", "preview_image_3", "preview_image_4",
                      "categories"}

    clean = {k: data.get(k) for k in allowed_fields}

    if clean.get("brand_name") is not None:
        clean["brand_name"] = clean["brand_name"].strip()
        if not clean["brand_name"]:
            raise Exception("brand_name cannot be empty.")

    clean["categories"] = normalize_storefront_categories(clean.get("categories"))

    return update_storefront(
        storefront_id=storefront_id,
        brand_name=clean.get("brand_name"),
        bio=clean.get("bio"),
        logo_url=clean.get("logo_url"),
        banner_url=clean.get("banner_url"),
        contact_info=clean.get("contact_info"),
        preview_image_1=clean.get("preview_image_1"),
        preview_image_2=clean.get("preview_image_2"),
        preview_image_3=clean.get("preview_image_3"),
        preview_image_4=clean.get("preview_image_4"),
        categories=clean.get("categories"),
    )


def deactivate_storefront_service(current_user, storefront_id):
    """
    Soft-deactivates a storefront (sets is_active = False).
    """

    if not current_user:
        raise Exception("Error! Unauthorized User.")

    storefront = get_storefront_by_id(storefront_id)
    if not storefront:
        raise Exception("Storefront not found.")

    is_owner = (storefront["owner_id"] == current_user["id"])
    if not is_owner and not is_admin(current_user):
        raise Exception("Unauthorized action.")

    updated = set_storefront_active(storefront_id, False)
    deactivate_storefront_listings_service(storefront_id)
    return updated


def reactivate_storefront_service(current_user, storefront_id):
    """
    Restores a previously deactivated storefront and any listings paused by that storefront shutdown.
    """
    if not current_user:
        raise Exception("Error! Unauthorized User.")

    storefront = get_storefront_by_id(storefront_id)
    if not storefront:
        raise Exception("Storefront not found.")

    is_owner = (storefront["owner_id"] == current_user["id"])
    if not is_owner and not is_admin(current_user):
        raise Exception("Unauthorized action.")

    updated = set_storefront_active(storefront_id, True)
    restore_storefront_listings_service(storefront_id)
    return updated
