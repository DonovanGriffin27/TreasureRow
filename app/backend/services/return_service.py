"""
return_service.py

Business rules and validation for return requests.
"""

from models.return_model import create_return_record, get_all_returns, update_return_status

VALID_RETURN_STATUSES = {"pending", "reviewed", "resolved"}


def _normalize_has_damage(value):
    if isinstance(value, bool):
        return value

    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "y", "1"}:
        return True
    if normalized in {"false", "no", "n", "0"}:
        return False
    raise Exception("has_damage is required.")


def create_return_service(current_user, data, damage_image_url=None):
    if not current_user or not current_user.get("id"):
        raise Exception("Unauthorized.")

    order_number = str(data.get("order_number") or "").strip()
    reason = str(data.get("reason") or "").strip()
    raw_has_damage = data.get("has_damage")

    if not order_number:
        raise Exception("order_number is required.")
    if not reason:
        raise Exception("reason is required.")
    if raw_has_damage in (None, ""):
        raise Exception("has_damage is required.")

    has_damage = _normalize_has_damage(raw_has_damage)

    return create_return_record(
        user_id=current_user["id"],
        order_number=order_number,
        reason=reason,
        has_damage=has_damage,
        damage_image_url=damage_image_url,
        status="pending",
    )


def fetch_returns_service():
    return get_all_returns(include_deleted=False)


def update_return_status_service(return_id, status):
    normalized_status = str(status or "").strip().lower()
    if normalized_status not in VALID_RETURN_STATUSES:
        raise Exception("status must be pending, reviewed, or resolved.")

    updated = update_return_status(return_id, normalized_status)
    if updated is None:
        raise Exception("Return not found.")
    return updated
