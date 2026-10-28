# backend/tests/conftest.py
# Created by Donovan Griffin - Iteration 3
#
# Loaded by pytest before any test module. Points the test suite at a
# separate TEST database so tests never write fake users/listings into the
# team's live AWS RDS database.
#
# Setup (once):
#   createdb treasurerow_test
#   cp .env.test.example .env.test      # then fill in your local values
#
# Run (from app/app):
#   python3 -m pytest backend/tests

import os
import sys

import pytest
from dotenv import load_dotenv

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# .env.test wins over .env; real environment variables win over both
_env_test = os.path.join(APP_DIR, ".env.test")
if os.path.exists(_env_test):
    for key, value in __import__("dotenv").dotenv_values(_env_test).items():
        os.environ.setdefault(key, value or "")
load_dotenv(os.path.join(APP_DIR, ".env"))

# tests never upload to the real S3 bucket; s3.py falls back to static/uploads/
for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_S3_BUCKET"):
    os.environ[key] = ""

# refuse to run against the shared AWS database
if "amazonaws.com" in os.getenv("DB_HOST", "") and os.getenv("ALLOW_REMOTE_TEST_DB") != "1":
    pytest.exit(
        "Refusing to run tests against the live AWS database "
        f"(DB_HOST={os.getenv('DB_HOST')}). Create a local test database and a "
        ".env.test file - see backend/tests/conftest.py.",
        returncode=2,
    )

# make app.py, the backend modules, and helpers.py importable from every test file
for path in (APP_DIR, os.path.join(APP_DIR, "backend"), os.path.dirname(__file__)):
    if path not in sys.path:
        sys.path.insert(0, path)
