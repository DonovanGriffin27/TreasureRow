"""
account_controller.py
Handles fetching profile details, student verification status, 
and user-specific activity (purchases/postings).


from flask import Blueprint, jsonify
from db import get_connection

account_bp = Blueprint('account_bp', __name__, url_prefix='/api/account')

@account_bp.route('/<int:user_id>', methods=['GET'])
def get_user_profile(user_id):
    Retrieves full account details for a specific student.
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        # Fetch basic user info
        cur.execute("SELECT username, email, role FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        
        if not user:
            return jsonify({"error": "User not found"}), 404

        # Fetch the user's listings (Postings) if they have a storefront
        cur.execute(
            SELECT l.title, l.price 
            FROM listings l 
            JOIN storefronts s ON l.storefront_id = s.id 
            WHERE s.user_id = %s
        , (user_id,))
        postings = [{"title": r[0], "price": float(r[1])} for r in cur.fetchall()]

        # Construct profile object matching Functional Specs
        profile = {
            "name": user[0],
            "email": user[1],
            "role": user[2],
            "postings": postings,
            "payments": ["Visa **** 1234"], # Placeholder for payment logic
            "purchases": [] # Placeholder for order history logic
        }
        
        return jsonify(profile), 200
    finally:
        cur.close()
        conn.close()
        """