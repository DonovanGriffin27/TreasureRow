# Chase Jones
from flask import session

def get_current_user():
    user_id = session.get("user_id")
    if user_id is None:
        return None
    try:
        return {"id": int(user_id), "role": session.get("role") or "user"}
    except (TypeError, ValueError):
        return None
