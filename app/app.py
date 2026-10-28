import sys
import os
from urllib.parse import urlparse
from flask import Flask, render_template, redirect, url_for, session, request, jsonify
#Cameron Ridgley edited 10/01
# Edited by Cameron Ridgley - 10/27/26 - registered the Discover page and API blueprints (browse_controller.py)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from controllers.listing_controller import listing_bp
from controllers.storefront_controller import storefront_bp, storefront_pages_bp
from controllers.purchase_controller import purchase_bp
from controllers.wishlist_controller import wishlist_bp
from controllers.admin_controller import admin_bp
from controllers.auth_controller import auth_bp
from controllers.return_controller import returns_bp
from controllers.checkout_controller import checkout_bp
from controllers.wallet_controller import wallet_bp  # Treasure Tokens - Iteration 3
from controllers.browse_controller import browse_bp, browse_pages_bp  # Discover pages - Cameron Ridgley 10/27/26
from init_db import create_vault_tables


def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    app.secret_key = os.getenv("SECRET_KEY") # pull secret key from .env

    # largest request Flask will accept (up to 4 listing images of 5 MB each,
    # plus form fields); bigger requests get HTTP 413 - Donovan Griffin, Iteration 3
    app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024
    if not app.secret_key:
        # without a key every login silently breaks; stop instead - Iteration 3
        raise RuntimeError("SECRET_KEY is not set. Add SECRET_KEY to your .env file (see .env.example).")

    # Session cookie hardening - Donovan Griffin, Iteration 3
    #  - SameSite=Lax: browsers don't send the login cookie on form posts from
    #    other websites (blocks most CSRF)
    #  - HttpOnly: page scripts can't read the cookie
    #  - Secure: set SESSION_COOKIE_SECURE=1 once the site is served over HTTPS
    app.config.update(
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE") == "1",
    )

    # Run DB migrations on every startup so new columns are always present
    try:
        from init_db import create_vault_tables
        create_vault_tables()
    except Exception as _db_init_err:
        print(f"[startup] DB migration warning: {_db_init_err}")

    # Pages a signed-out visitor may see. Everything else requires a login.
    # Added by Donovan Griffin, Iteration 3
    PUBLIC_ENDPOINTS = {"index", "auth.login", "auth.signup", "auth.admin_login", "static", "health"}

    @app.before_request
    def block_cross_site_writes():
        # second CSRF layer: refuse state-changing requests that a browser
        # says came from another website - Donovan Griffin, Iteration 3
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            origin = request.headers.get("Origin")
            if origin and urlparse(origin).netloc != request.host:
                if "/api/" in request.path:
                    return jsonify({"error": "Cross-site request refused."}), 403
                return "Cross-site request refused.", 403
        return None

    @app.before_request
    def require_login():
        if session.get("user") or request.endpoint in PUBLIC_ENDPOINTS:
            return None
        # data requests from page scripts get a 401 instead of the login page HTML
        if "/api/" in request.path or request.path.endswith("/json") or request.accept_mimetypes.best == "application/json":
            return jsonify({"error": "Please sign in."}), 401
        return redirect(url_for("auth.login"))

    #The Welcome Screen (Default) 3/19/2026
    # Signed-out visitors see the landing page; signed-in users go straight
    # to the storefront home - Updated by Donovan Griffin, Iteration 3
    @app.route('/')
    def index():
         if not session.get("user"):
            return render_template('index.html')
         else:
            return redirect(url_for("auth.listings"))

    # Route to the main storefront page after login - Updated 3/22/2026
    @app.route('/storefront')
    def storefront():
         if not session.get("user"):
            return redirect(url_for("auth.login"))
         else:
            return render_template('storefront.html')

    # Route to the "Create Storefront" form - Updated 3/22/2026
    @app.route('/create-storefront')
    def create_storefront():
        return render_template('create_storefront.html')

    # Route to the "Create Listing" form - Updated 3/24/2026
    @app.route('/create-listing')
    def create_listing():
        return render_template('create_listing.html')

    #Route to the Cart screen - Updated 3/22/2026
    @app.route('/cart')
    def cart():
         if not session.get("user"):
            return redirect(url_for("auth.login"))
         else:
            return render_template('cart.html')

    #Route to the Checkout - Updated 4/22/2026
    @app.route('/checkout')
    def checkout():
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        return render_template('checkout.html')

    # Route to the Order Confirmation page - Added 4/22/2026
    @app.route('/order-confirmation')
    def order_confirmation():
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        return render_template('order_confirmation.html')
    
    # Route to My Storefront dashboard page - Updated 4/9/2026
    @app.route('/my-storefront')
    def my_storefront():
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        return render_template('my_storefront.html')

    # Route to the About page - Added by Donovan Griffin, Iteration 3
    # (fixes the "About" storefront nav link, previously commented out with no destination)
    @app.route('/about')
    def about():
        return render_template('about.html')

    # Route to the Sitemap page - Added by Donovan Griffin, Iteration 3
    # (fixes the "Sitemap" storefront nav link, previously commented out with no destination)
    @app.route('/sitemap')
    def sitemap():
        return render_template('sitemap.html')

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(listing_bp)
    app.register_blueprint(storefront_bp)
    app.register_blueprint(storefront_pages_bp)
    app.register_blueprint(purchase_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(returns_bp)
    app.register_blueprint(checkout_bp, url_prefix='/api')
    app.register_blueprint(wallet_bp)
    app.register_blueprint(browse_bp)
    app.register_blueprint(browse_pages_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app

app = create_app()

if __name__ == "__main__":
    # port 5001: macOS AirPlay Receiver already listens on 5000 - Donovan Griffin, Iteration 3
    app.run(debug=True, port=int(os.getenv("PORT", 5001)))
