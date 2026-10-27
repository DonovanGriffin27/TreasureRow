import sys
import os
import secrets
from flask import Flask, render_template, redirect, url_for, session
#Cameron Ridgley edited 10/01
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))) # Updated 3/19/2026 by Ryan Grimes

from controllers.listing_controller import listing_bp
from controllers.storefront_controller import storefront_bp, storefront_pages_bp  # Updated by Day E 3/22/26
from controllers.purchase_controller import purchase_bp
from controllers.wishlist_controller import wishlist_bp
from controllers.admin_controller import admin_bp
from controllers.auth_controller import auth_bp # Updated 3/19/2026 by Ryan Grimes
from controllers.return_controller import returns_bp
from controllers.checkout_controller import checkout_bp
from init_db import create_vault_tables


def create_app():
    app = Flask(__name__,
                template_folder='templates',
                static_folder='static')

    # Chase Jones
    placeholder_keys = {"", "change-me", "change_me", "changeme", "dev-secret", "secret"}
    secret_key = (os.getenv("SECRET_KEY") or "").strip()
    if secret_key.lower() in placeholder_keys:
        if os.getenv("FLASK_ENV", "").lower() == "development":
            secret_key = secrets.token_hex(32)
            print("[security] SECRET_KEY not set - using a temporary random key (development only).")
        else:
            raise RuntimeError(
                "SECRET_KEY is missing or still a placeholder. Set a long random value "
                "(e.g. `python -c \"import secrets; print(secrets.token_hex(32))\"`) in the "
                "environment (eb setenv SECRET_KEY=...)."
            )
    app.secret_key = secret_key

    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true",
        MAX_CONTENT_LENGTH=20 * 1024 * 1024,
    )

    # Chase Jones
    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    # Run DB migrations on every startup so new columns are always present
    try:
        from init_db import create_vault_tables
        create_vault_tables()
    except Exception as _db_init_err:
        print(f"[startup] DB migration warning: {_db_init_err}")

    #The Welcome Screen (Default) Ryan Grimes 3/19/2026
    @app.route('/')
    def index():
         if not session.get("user"):
            return redirect(url_for("auth.login"))
         else:
            return render_template('index.html')

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
        if not session.get("user"):
            return redirect(url_for("auth.login"))
        return render_template('create_storefront.html')

    # Route to the "Create Listing" form - Updated 3/24/2026
    @app.route('/create-listing')
    def create_listing():
        if not session.get("user"):
            return redirect(url_for("auth.login"))
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
    app.register_blueprint(storefront_pages_bp)  # Updated by Day E 3/22/26
    app.register_blueprint(purchase_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(admin_bp) # Updated 3/19/2026 by Ryan Grimes
    app.register_blueprint(returns_bp)
    app.register_blueprint(checkout_bp, url_prefix='/api')

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
