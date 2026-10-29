# Treasure Row Campus Marketplace
# Added by Cameron Ridgley - 10/27/26

"""
browse_controller.py

Purpose:
Page routes and the data route for the Discover pages listed under "More" in
the slide-out menu: Explore Brands, All Categories, New Drops, and Hot!.

Explore Brands and All Categories load brands from GET /api/storefronts.
New Drops and Hot! load listings from every brand via GET /api/browse/listings.

All four pages require a signed-in user (enforced by require_login in app.py).
"""

from flask import Blueprint, jsonify, render_template, request

from services.browse_service import get_browse_listings_service

# Page blueprint
browse_pages_bp = Blueprint("browse_pages_bp", __name__)

# API blueprint
browse_bp = Blueprint("browse_bp", __name__, url_prefix="/api/browse")


#_________________________________________________________
# Page Routing
#_________________________________________________________

@browse_pages_bp.route("/explore-brands")
def explore_brands_page():
    return render_template("explore_brands.html")


@browse_pages_bp.route("/categories")
def categories_page():
    return render_template("categories.html")


@browse_pages_bp.route("/new-drops")
def new_drops_page():
    return render_template("new_drops.html")


@browse_pages_bp.route("/hot")
def hot_page():
    return render_template("hot.html")


#_________________________________________________________
# API Routing
#_________________________________________________________

# Listings from every active storefront
# GET /api/browse/listings?sort=new|hot&limit=60
@browse_bp.get("/listings")
def get_browse_listings_route():
    try:
        listings = get_browse_listings_service(
            sort=request.args.get("sort", "new"),
            raw_limit=request.args.get("limit"),
        )
        return jsonify(listings), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        print(f"[browse] listings error: {e}")
        return jsonify({"error": "Could not load listings."}), 500
