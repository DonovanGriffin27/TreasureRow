# The Vault Campus Marketplace
# CSC 405 Sp 26'

import secrets
import string
from datetime import datetime

from models.listing_model import get_listing_by_id
from services import wallet_service
from models.checkout_model import (
    create_order,
    create_order_item,
    get_order_by_confirmation,
    get_order_items_by_order_id,
    get_orders_by_user_id,
    clear_cart_for_user,
    update_listing_size_inventory,
    remove_purchased_from_wishlist,
    check_listing_availability,
    delete_order,
)


def _generate_confirmation_number():
    date_str = datetime.now().strftime("%y%m%d")
    # Noah Higgs
    suffix = "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
    return f"TR-{date_str}-{suffix}"  # was VAULT-; renamed for Treasure Row (Iteration 3)


def _price_cart_from_database(session_cart):
    """Return the cart rebuilt from listing data: real title + price, validated quantity."""
    priced = []
    for item in session_cart:
        try:
            listing_id = int(item.get("id"))
            quantity = int(item.get("quantity", 1))
        except (TypeError, ValueError):
            raise Exception("Your bag has an item that is no longer available. Please remove it and try again.")
        if quantity < 1:
            raise Exception("Item quantities must be at least 1.")

        listing = get_listing_by_id(listing_id)
        if listing is None or listing["status"] in ("DELETED", "INACTIVE"):
            raise Exception(f"Item (ID {listing_id}) is no longer available.")
        check_listing_availability(listing_id, quantity)

        priced.append({
            "id": listing_id,
            "name": listing["title"],
            "price": float(listing["price"]),
            "quantity": quantity,
            "size": item.get("size"),
        })
    return priced


def complete_transaction_from_session(user_id, session_cart, buyer_details):
    """
    Completes checkout using session cart and submitted buyer details.

    buyer_details keys: first_name, last_name, email, contact, meeting_location
    session_cart items: { id, name, price, quantity, size }
    """
    if not session_cart:
        raise Exception("Cart is empty.")

    # Re-price every cart item from the database: the cart's own price/name
    # came from the browser (and older carts may hold tampered prices), so it
    # is never trusted. Every item must be a real, available listing.
    # Updated by Donovan Griffin, Iteration 3
    session_cart = _price_cart_from_database(session_cart)

    first_name = (buyer_details.get("first_name") or "").strip()
    last_name = (buyer_details.get("last_name") or "").strip()
    email = (buyer_details.get("email") or "").strip()
    contact = (buyer_details.get("contact") or "").strip()
    meeting_location = (buyer_details.get("meeting_location") or "").strip()

    if not all([first_name, last_name, email, contact, meeting_location]):
        raise Exception("All buyer details are required.")

    total_amount = round(
        sum(float(item.get("price", 0)) * int(item.get("quantity", 1)) for item in session_cart),
        2,
    )

    # Treasure Tokens: work out each seller's share and make sure the buyer can
    # afford it before anything is written - Donovan Griffin, Iteration 3
    portions = wallet_service.seller_portions(session_cart)
    wallet_service.assert_can_afford(user_id, total_amount)

    confirmation_number = _generate_confirmation_number()

    order = create_order(
        user_id=user_id,
        confirmation_number=confirmation_number,
        buyer_first_name=first_name,
        buyer_last_name=last_name,
        buyer_email=email,
        buyer_contact=contact,
        buyer_meeting_location=meeting_location,
        total_amount=total_amount,
    )

    # Move the tokens into escrow (one locked transaction). If that fails -
    # e.g. the balance changed since the check above - remove the unpaid order.
    try:
        escrows = wallet_service.hold_escrow(order["id"], user_id, portions)
    except Exception:
        delete_order(order["id"])
        raise

    order_items = []
    for item in session_cart:
        item_id = item.get("id")
        item_name = item.get("name", "Item")
        quantity = int(item.get("quantity", 1))
        price = float(item.get("price", 0))
        size = item.get("size")

        order_item = create_order_item(
            order_id=order["id"],
            listing_id=item_id,
            item_name=item_name,
            quantity=quantity,
            price_at_purchase=price,
            selected_size=size,
        )
        order_items.append(order_item)

        if item_id and size:
            try:
                update_listing_size_inventory(int(item_id), size, quantity)
            except Exception as e:
                print(f"[checkout] inventory update failed for listing {item_id} size {size}: {e}")

    clear_cart_for_user(user_id)

    # Remove purchased listings from the user's wishlist
    purchased_listing_ids = [item.get("id") for item in session_cart if item.get("id") is not None]
    try:
        remove_purchased_from_wishlist(user_id, purchased_listing_ids)
    except Exception as e:
        print(f"[checkout] wishlist cleanup failed: {e}")

    return {
        "confirmation_number": confirmation_number,
        "order": order,
        "order_items": order_items,
        "total_amount": total_amount,
        "escrows": escrows,
    }


def get_order_summary_service(confirmation_number, user_id):
    """Returns order + items for the confirmation page. Validates user ownership."""
    order = get_order_by_confirmation(confirmation_number)
    if not order:
        raise Exception("Order not found.")
    if order["user_id"] != user_id:
        raise Exception("Access denied.")
    items = get_order_items_by_order_id(order["id"])
    escrows = wallet_service.order_escrows_for_buyer(order["id"], user_id)
    return {"order": order, "order_items": items, "escrows": escrows}


def get_user_orders_service(user_id):
    """Returns all orders for the given user, newest first."""
    return get_orders_by_user_id(user_id)
