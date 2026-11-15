# Package
"""
IMPORTANT:
Do NOT delete this file.

This file marks this folder as a Python package.

Even though it may appear empty, it allows Python to properly
recognize this directory as a package so imports like:

    from controllers.storefront_controller import storefront_bp
    from models.listing_model import create_listing

work correctly.

Removing this file can cause ModuleNotFoundError or import failures.
"""

# Chase Jones - Iteration 4
# Single place the app's version number is written. app.py copies it into
# app.config["APP_VERSION"], which puts it in reach of every template as
# {{ config.APP_VERSION }} and of the /health endpoint. Bump it here only.
APP_VERSION = "0.4-beta"
