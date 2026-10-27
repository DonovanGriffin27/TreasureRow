# By Ryan Grimes - Updated 3/19/2026 | Edited by Jonah Goodwine 9/30
import os
import hmac
import logging
from markupsafe import escape
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify
from services.auth_services import AuthService 
from config.db import get_connection
from models.auth_model import get_user_by_username, get_listing_for_cart, add_cart_item, remove_cart_item

auth_bp = Blueprint('auth', __name__)
service = AuthService()
logger = logging.getLogger(__name__)

MAX_CART_QUANTITY = 20


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = (request.form.get('username') or '').strip()
        pw = request.form.get('password') or ''

        conn = get_connection()
        if conn is None:
            return "Database connection failed. <a href='/auth/login'>Try again</a>"

        try:
            success, role = service.validate_login(user, pw, conn)

            if not success:
                return "Invalid Credentials. <a href='/auth/login'>Try again</a>"

            session.clear()
            session['user'] = user
            session['role'] = role

            #store user_id in sesion for storefront ownership checks - added by Day E 4/9/26
            try:
                row = get_user_by_username(user)
                if row:
                    session['user_id'] = row[0] # Store user_id in session
                    session['cart'] = service.get_user_cart(conn, row[0]) # Load user's cart into session on login
            except Exception:
                logger.exception("Error fetching user_id for session")
        finally:
            conn.close()

        # Redirect based on role - added by David Jackson 3/23/2026
        if role and role.lower() == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('auth.listings'))
    
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user = request.form.get('username') 
        pw = request.form.get('password')
        email = request.form.get('email')

        conn = get_connection()
        if conn is None:
            return "Database connection failed. <a href='/auth/signup'>Try again</a>"

        try:
            success, message = service.register_user(user, pw, email, conn)
        finally:
            conn.close()

        if success:
            flash("Signup Successful! Please login with your new credentials.", "success")
            return redirect(url_for('auth.login'))
        return f"Signup Failed: {escape(message)} <a href='/auth/signup'>Try again</a>"
    
    return render_template('signup.html')

@auth_bp.route('/listings')
def listings():
    if 'user' not in session:
        return redirect(url_for('auth.login'))
    return render_template('storefront.html')

@auth_bp.route('/account')
def account():
    if 'user' not in session: 
        return redirect(url_for('auth.login'))
    return render_template('account.html')
    
@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/cart')
def view_cart():
    if 'cart' not in session:
        session['cart'] = []
    return render_template('cart.html')

@auth_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        flash("Please login to add items to your bag.", "error")
        return redirect(url_for('auth.login'))

    try:
        item_id = int(request.form.get('item_id', ''))
        quantity = int(request.form.get('quantity', 1))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid item or quantity."}), 400
    if not (1 <= quantity <= MAX_CART_QUANTITY):
        return jsonify({"error": f"Quantity must be between 1 and {MAX_CART_QUANTITY}."}), 400
    size = (request.form.get('size') or '').strip()[:50] or None

    try:
        listing = get_listing_for_cart(item_id)
    except Exception:
        logger.exception("DB error looking up listing for cart")
        return jsonify({"error": "Could not add this item right now. Please try again."}), 503

    if not listing or listing[2] in ("INACTIVE", "DELETED"):
        return jsonify({"error": "This item is no longer available."}), 404

    item_name, price, listing_status, qty_on_hand, is_made_to_order = listing
    price = float(price)
    if not is_made_to_order and (
        listing_status == "SOLD_OUT" or (qty_on_hand is not None and int(qty_on_hand) < quantity)
    ):
        return jsonify({"error": f"{item_name} is sold out or doesn't have enough stock for that quantity."}), 409

    # PERSIST TO DATABASE
    try:
        add_cart_item(session['user_id'], item_id, item_name, price, quantity, size)
    except Exception:
        logger.exception("DB error adding to cart")
        return jsonify({"error": "Could not save your bag. Please try again."}), 500

    # Update session for immediate UI feedback
    if 'cart' not in session:
        session['cart'] = []
    
    cart_item = {'id': item_id, 'name': item_name, 'price': price, 'quantity': quantity, 'size': size}
    temp_cart = session['cart']
    temp_cart.append(cart_item)
    session['cart'] = temp_cart
    session.modified = True

    flash(f"Added {item_name} to your bag!", "success")
    return redirect(url_for('auth.view_cart'))

@auth_bp.route('/remove_from_cart/<int:index>', methods=['POST'])
def remove_from_cart(index):
    if 'cart' in session and 'user_id' in session:
        temp_cart = session['cart']
        if 0 <= index < len(temp_cart):
            removed_item = temp_cart.pop(index)
            
            # REMOVE FROM DATABASE
            try:
                remove_cart_item(session['user_id'], removed_item['name'], removed_item['size'])
            except Exception:
                logger.exception("DB error removing cart item")

            session['cart'] = temp_cart
            session.modified = True
            flash(f"Removed {removed_item['name']} from bag.", "info")
    return redirect(url_for('auth.view_cart'))

# Added by Day E 4/9/26 - returns current session user info for frontend auth checks
@auth_bp.route('/api/auth/me')
def get_current_session_user():
    if 'user' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        user = get_user_by_username(session['user'])

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({
            "id": user[0],
            "username": user[1],
            "role": user[2]
        }), 200

    except Exception:
        logger.exception("Error loading current user")
        return jsonify({"error": "Could not load your account right now."}), 500
    
@auth_bp.route('/cart/json')
def get_cart_json():
    return jsonify(session.get('cart', []))


# Admin login route - added by David Jackson 4/19/26
@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('username') or ''
        pw = request.form.get('password') or ''

        # admin login pulled from .env (changed from temp hardcode)
        adminUser = os.getenv("ADMIN_USERNAME")
        adminPass = os.getenv("ADMIN_PASSWORD")

        user_ok = bool(adminUser) and hmac.compare_digest(user.encode("utf-8"), adminUser.encode("utf-8"))
        pass_ok = bool(adminPass) and hmac.compare_digest(pw.encode("utf-8"), adminPass.encode("utf-8"))
        if user_ok and pass_ok:
            session.clear()
            session['user'] = user
            session['role'] = 'admin'
            return redirect(url_for('admin.admin_dashboard'))

        return "Invalid Admin Credentials. <a href='/auth/admin-login'>Try again</a>"

    return render_template('admin_login.html')
