# Treasure Row Campus Marketplace
# Added by Cameron Ridgley - 10/27/26

"""
browse_service.py

Purpose: rules for the Discover pages (New Drops and Hot!).

What it does:
- Validates the sort the page asked for ("new" or "hot")
- Keeps the number of listings returned between 1 and MAX_LIMIT
- Calls the model file (browse_model.py) to run the SQL query
"""

from models.browse_model import ORDER_BY, get_public_listings

DEFAULT_LIMIT = 60
MAX_LIMIT = 100


def parse_limit(raw_limit):
    """Turns the ?limit= query value into a whole number from 1 to MAX_LIMIT."""
    if raw_limit in (None, ""):
        return DEFAULT_LIMIT
    try:
        limit = int(raw_limit)
    except (TypeError, ValueError):
        raise ValueError("limit must be a whole number.")
    return max(1, min(limit, MAX_LIMIT))


def get_browse_listings_service(sort="new", raw_limit=None):
    """Listings from every active storefront, sorted for New Drops or Hot!."""
    sort = (sort or "new").strip().lower()
    if sort not in ORDER_BY:
        raise ValueError("sort must be 'new' or 'hot'.")
    return get_public_listings(sort=sort, limit=parse_limit(raw_limit))
