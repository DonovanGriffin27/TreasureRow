# Updated 3/19/2026 | Edited by Jonah Goodwine 9/30
import os
from flask import Blueprint, request, session, redirect, url_for, render_template, flash, jsonify
from services.auth_services import AuthService 
from config.db import get_connection
from models.auth_model import get_user_by_username, add_cart_item, remove_cart_item
from models.listing_model import get_listing_by_id

auth_bp = Blueprint('auth', __name__)
service = AuthService()

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')

        conn = get_connection()
        if conn is None:
            return render_template('login.html', error="We couldn't reach the database. Please try again in a moment.", username=user), 503

        success, role = service.validate_login(user, pw, conn)
        # conn.close()
        
        if success:
            session['user'] = user
            session['role'] = role

            #store user_id in sesion for storefront ownership checks - added 4/9/26
            try:
                row = get_user_by_username(user)
                if row:
                    session['user_id'] = row[0] # Store user_id in session
                    session['cart'] = service.get_user_cart(conn, row[0]) # Load user's cart into session on login
            except Exception as e:
                print(f"Error fetching user_id for session: {e}")
            finally:
                conn.close()

            #return redirect(url_for('auth.listings'))
            # Redirect based on role - added 3/23/2026
            if role and role.lower() == 'admin':
                return redirect(url_for('admin.admin_dashboard'))
            else:
                return redirect(url_for('auth.listings'))
        
        # Noah Higgs
        # a failed login must not leave its database connection open
        conn.close()
        # errors now show on the form instead of a bare text page - Donovan Griffin, Iteration 3
        return render_template('login.html', error="Incorrect username or password.", username=user), 401
    
    return render_template('login.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        user = request.form.get('username') 
        pw = request.form.get('password')
        email = request.form.get('email')

        conn = get_connection()
        if conn is None:
            return render_template('signup.html', error="We couldn't reach the database. Please try again in a moment.", username=user, email=email), 503

        success, message = service.register_user(user, pw, email, conn)
        conn.close()

        if success:
            flash("Signup Successful! Please login with your new credentials.", "success")
            return redirect(url_for('auth.login'))
        return render_template('signup.html', error=f"Couldn't create your account: {message}", username=user, email=email), 400
    
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

    # The name and price always come from the database, never from the form:
    # the browser can send any price it wants (e.g. $0.01 for a $40 item).
    # Quantity and listing status are validated before anything is added.
    # Updated by Donovan Griffin, Iteration 3
    try:
        item_id = int(request.form.get('item_id', ''))
        listing = get_listing_by_id(item_id)
    except (TypeError, ValueError):
        listing = None
    except Exception as e:
        print(f"DB Error loading listing for cart: {e}")
        return jsonify({"error": "Couldn't add this item right now. Please try again."}), 503
    if not listing or listing["status"] in ("DELETED", "INACTIVE"):
        return jsonify({"error": "This item is no longer available."}), 404

    item_name = listing["title"]
    price = listing["price"]
    size = (request.form.get('size') or '').strip()[:50] or None

    quantity_raw = (request.form.get('quantity') or '1').strip()
    if not quantity_raw.isdigit() or int(quantity_raw) < 1:
        return jsonify({"error": "Quantity must be a whole number of at least 1."}), 400
    quantity = int(quantity_raw)

    qty_on_hand = listing["quantity_on_hand"]
    if not listing["is_made_to_order"]:
        if listing["status"] == "SOLD_OUT" or (qty_on_hand is not None and int(qty_on_hand) <= 0):
            return jsonify({"error": f"{item_name} is sold out and cannot be added to your bag."}), 409
        if qty_on_hand is not None and quantity > int(qty_on_hand):
            return jsonify({"error": f"Only {qty_on_hand} of {item_name} in stock."}), 409

    # PERSIST TO DATABASE
    try:
        add_cart_item(session['user_id'], item_id, item_name, price, quantity, size)
    except Exception as e:
        print(f"DB Error adding to cart: {e}")

    # Update session for immediate UI feedback
    if 'cart' not in session:
        session['cart'] = []
    
    cart_item = {'id': item_id, 'name': item_name, 'price': float(price), 'quantity': int(quantity), 'size': size}
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
            except Exception as e:
                print(f"DB Error removing item: {e}")

            session['cart'] = temp_cart
            session.modified = True
            flash(f"Removed {removed_item['name']} from bag.", "info")
    return redirect(url_for('auth.view_cart'))

# Added 4/9/26 - returns current session user info for frontend auth checks
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

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@auth_bp.route('/cart/json')
def get_cart_json():
    return jsonify(session.get('cart', []))

# Admin login route - added 4/19/26
@auth_bp.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')

        # admin login pulled from .env (changed from temp hardcode)
        adminUser = os.getenv("ADMIN_USERNAME")
        adminPass = os.getenv("ADMIN_PASSWORD")
        if adminUser and adminPass and user == adminUser and pw == adminPass:
            session['user'] = user
            session['role'] = 'admin'
            return redirect(url_for('admin.admin_dashboard'))

        return render_template('admin_login.html', error="Incorrect admin username or password.", username=user), 401

    return render_template('admin_login.html')