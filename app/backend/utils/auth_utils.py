#Hashes passwords and verifies hashes

from werkzeug.security import generate_password_hash, check_password_hash #Werkzeug handles requests and responses between web servers and .security is the submodule for hashing and data protection.

def hash_password(password):
    return generate_password_hash(password, method='pbkdf2:sha256') #Hashes the password using the pbkdf2:sha256 algorithm

def verify_password(hashed_password, password): 
    return check_password_hash(hashed_password, password) #Compares hash of inputted password to hash of storred password for that username


# Added by Donovan Griffin, Iteration 3 - fixes the ownership/impersonation bug.
# Controllers used to read identity from X-User-Id / X-User-Role request
# headers, which any client can set (e.g. X-User-Id: 5, X-User-Role: admin)
# to act as another user or as an admin. Identity now comes only from the
# server-side session that is set at login.
def get_session_user():
    """Return {"id", "role"} for the signed-in user, or None if not signed in.

    Never reads identity from request headers, query strings, or bodies.
    """
    from flask import session

    if not session.get("user"):
        return None

    role = session.get("role") or "user"
    user_id = session.get("user_id")

    if user_id is None:
        # the .env admin account (admin-login) has no row in users
        return {"id": None, "role": "admin"} if role == "admin" else None

    try:
        return {"id": int(user_id), "role": role}
    except (TypeError, ValueError):
        return None
