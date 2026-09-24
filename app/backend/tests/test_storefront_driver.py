# The Vault Campus Marketplace
# CSC 405 Sp 26'
# Created by Day Ekoi - Iteration 5 - 4/21/26
# Purpose: Integration test driver for all storefront features.
#          Covers model layer (direct DB), schema constraints, service layer (rules, validation, permissions),
#          and API routes (HTTP via Flask test client). Tests real database on AWS RDS.

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from db import get_connection
from models.storefront_model import (
    create_storefront,
    get_storefront_by_id,
    get_storefront_by_owner_id,
    update_storefront,
    set_storefront_active,
    get_all_storefronts,
    get_active_storefronts,
)
from services.storefront_service import (
    create_storefront_service,
    get_my_storefront_service,
    update_storefront_service,
    deactivate_storefront_service,
)


# ________________________________________________________
# TEST UTILITIES
# ________________________________________________________

passed = 0
failed = 0

def check(label, condition, detail=""):
    global passed, failed
    if condition:
        print(f"  [PASS] {label}")
        passed += 1
    else:
        print(f"  [FAIL] {label}" + (f" — {detail}" if detail else ""))
        failed += 1

def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")

def subsection(title):
    print(f"\n  --- {title} ---")


def create_test_user(cur, conn, username, role="student"):
    """Helper: inserts a throwaway test user and returns their id."""
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        (username, f"{username}@vault-test.com", "testhash_placeholder", role)
    )
    conn.commit()
    return cur.fetchone()[0]


def print_db_state(cur):
    """Prints every row currently in the storefronts table."""
    print(f"\n{'=' * 60}")
    print("  CURRENT DATABASE STATE — storefronts table")
    print(f"{'=' * 60}")
    cur.execute("""
        SELECT s.id, s.owner_id, s.brand_name, s.bio, s.contact_info,
               s.categories, s.is_active, s.created_at,
               s.preview_image_1, s.preview_image_2, s.preview_image_3, s.preview_image_4,
               COUNT(l.id) AS item_count
        FROM storefronts s
        LEFT JOIN listings l ON l.storefront_id = s.id AND l.status NOT IN ('DELETED', 'INACTIVE')
        GROUP BY s.id
        ORDER BY s.id;
    """)
    rows = cur.fetchall()
    if not rows:
        print("  (no rows found)\n")
        return
    print(f"  Total rows: {len(rows)}\n")
    for row in rows:
        print(f"  ┌─ Storefront ID : {row[0]}")
        print(f"  │  Owner ID      : {row[1]}")
        print(f"  │  Brand Name    : {row[2]}")
        print(f"  │  Bio           : {row[3]}")
        print(f"  │  Contact Info  : {row[4]}")
        print(f"  │  Categories    : {row[5]}")
        print(f"  │  Is Active     : {row[6]}")
        print(f"  │  Created At    : {row[7]}")
        print(f"  │  Preview 1     : {row[8]}")
        print(f"  │  Preview 2     : {row[9]}")
        print(f"  │  Preview 3     : {row[10]}")
        print(f"  │  Preview 4     : {row[11]}")
        print(f"  └─ Item Count    : {row[12]}")
        print()


def cleanup(cur, conn, owner_ids):
    """Helper: removes all test storefronts and test users created during the run."""
    for uid in owner_ids:
        cur.execute("DELETE FROM storefronts WHERE owner_id = %s;", (uid,))
    cur.executemany("DELETE FROM users WHERE id = %s;", [(uid,) for uid in owner_ids])
    conn.commit()


# ________________________________________________________
# SECTION 1 — MODEL LAYER (Direct DB Tests)
# ________________________________________________________

def run_model_tests(cur, conn, owner_id):
    section("SECTION 1 — MODEL LAYER (Direct DB Tests)")
    print("  These call storefront_model.py functions directly and validate")
    print("  that rows are correctly inserted, retrieved, and updated in the DB.\n")

    # ----------------------------------------------------------
    # TEST 1.1 — create_storefront (full fields)
    # Description: Creates a storefront with all optional fields provided.
    #              Validates every returned key matches the input.
    # ----------------------------------------------------------
    subsection("TEST 1.1 — create_storefront: all fields provided")
    sf = create_storefront(
        owner_id=owner_id,
        brand_name="Vault Test Brand",
        bio="Test bio",
        logo_url="https://s3.example.com/logo.png",
        banner_url="https://s3.example.com/banner.png",
        contact_info="vault@hampton.edu",
        preview_image_1="https://s3.example.com/p1.png",
        preview_image_2="https://s3.example.com/p2.png",
        preview_image_3="https://s3.example.com/p3.png",
        preview_image_4="https://s3.example.com/p4.png",
        categories="Clothing, Accessories",
    )
    check("Returns a dict", isinstance(sf, dict))
    check("brand_name matches input", sf["brand_name"] == "Vault Test Brand")
    check("bio matches input", sf["bio"] == "Test bio")
    check("contact_info matches input", sf["contact_info"] == "vault@hampton.edu")
    check("preview_image_1 matches input", sf["preview_image_1"] == "https://s3.example.com/p1.png")
    check("preview_image_4 matches input", sf["preview_image_4"] == "https://s3.example.com/p4.png")
    check("categories matches input", sf["categories"] == "Clothing, Accessories")
    check("is_active defaults to True", sf["is_active"] is True)
    check("id is assigned (not None)", sf["id"] is not None)
    check("owner_id matches", sf["owner_id"] == owner_id)
    storefront_id = sf["id"]

    # ----------------------------------------------------------
    # TEST 1.2 — create_storefront (minimal — brand_name only)
    # Description: Creates a storefront with only the required field.
    #              All optional fields should come back as None.
    # ----------------------------------------------------------
    subsection("TEST 1.2 — create_storefront: brand_name only (minimal)")
    # Need a second test user for this one (owner_id must be unique)
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("vault_minimal_user", "minimal@vault-test.com", "testhash_placeholder", "student")
    )
    conn.commit()
    minimal_owner_id = cur.fetchone()[0]

    sf_min = create_storefront(owner_id=minimal_owner_id, brand_name="Minimal Brand")
    check("brand_name set", sf_min["brand_name"] == "Minimal Brand")
    check("bio is None", sf_min["bio"] is None)
    check("logo_url is None", sf_min["logo_url"] is None)
    check("preview_image_1 is None", sf_min["preview_image_1"] is None)
    check("is_active defaults to True", sf_min["is_active"] is True)
    check("created_at is not None", sf_min["created_at"] is not None)
    check("updated_at is not None", sf_min["updated_at"] is not None)

    # ----------------------------------------------------------
    # TEST 1.3 — get_storefront_by_id (exists)
    # Description: Retrieves the storefront created in 1.1 by its primary key.
    #              Validates all fields and that item_count is present.
    # ----------------------------------------------------------
    subsection("TEST 1.3 — get_storefront_by_id: storefront exists")
    fetched = get_storefront_by_id(storefront_id)
    check("Returns a dict (not None)", fetched is not None)
    check("id matches", fetched["id"] == storefront_id)
    check("brand_name correct", fetched["brand_name"] == "Vault Test Brand")
    check("item_count key present", "item_count" in fetched)
    check("item_count is 0 (no listings yet)", fetched["item_count"] == 0)

    # ----------------------------------------------------------
    # TEST 1.4 — get_storefront_by_id (does not exist)
    # Description: Queries a storefront ID that was never inserted.
    #              Should return None without raising an exception.
    # ----------------------------------------------------------
    subsection("TEST 1.4 — get_storefront_by_id: storefront does not exist")
    result = get_storefront_by_id(999999999)
    check("Returns None for nonexistent ID", result is None)

    # ----------------------------------------------------------
    # TEST 1.5 — get_storefront_by_owner_id (exists)
    # Description: Retrieves the storefront using the owner's user ID.
    #              Validates the owner_id field and item_count presence.
    # ----------------------------------------------------------
    subsection("TEST 1.5 — get_storefront_by_owner_id: storefront exists")
    by_owner = get_storefront_by_owner_id(owner_id)
    check("Returns a dict (not None)", by_owner is not None)
    check("owner_id matches", by_owner["owner_id"] == owner_id)
    check("item_count key present", "item_count" in by_owner)

    # ----------------------------------------------------------
    # TEST 1.6 — get_storefront_by_owner_id (no storefront for user)
    # Description: Queries a user ID that has no storefront.
    #              Should return None.
    # ----------------------------------------------------------
    subsection("TEST 1.6 — get_storefront_by_owner_id: no storefront for user")
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("vault_no_store_user", "nostore@vault-test.com", "testhash_placeholder", "student")
    )
    conn.commit()
    no_store_uid = cur.fetchone()[0]
    result = get_storefront_by_owner_id(no_store_uid)
    check("Returns None when user has no storefront", result is None)
    cur.execute("DELETE FROM users WHERE id = %s;", (no_store_uid,))
    conn.commit()

    # ----------------------------------------------------------
    # TEST 1.7 — update_storefront (update fields)
    # Description: Updates bio, contact_info, and preview images on an existing storefront.
    #              Validates that changed fields reflect new values and untouched
    #              fields are preserved (COALESCE behavior).
    # ----------------------------------------------------------
    subsection("TEST 1.7 — update_storefront: update specific fields")
    updated = update_storefront(
        storefront_id=storefront_id,
        bio="Updated bio for test",
        contact_info="updated@hampton.edu",
        preview_image_2="https://s3.example.com/new_p2.png",
    )
    check("Returns updated dict", updated is not None)
    check("bio updated correctly", updated["bio"] == "Updated bio for test")
    check("contact_info updated correctly", updated["contact_info"] == "updated@hampton.edu")
    check("preview_image_2 updated", updated["preview_image_2"] == "https://s3.example.com/new_p2.png")
    check("brand_name preserved (COALESCE)", updated["brand_name"] == "Vault Test Brand")
    check("banner_url preserved (COALESCE)", updated["banner_url"] == "https://s3.example.com/banner.png")

    # ----------------------------------------------------------
    # TEST 1.8 — update_storefront (nonexistent ID)
    # Description: Attempts to update a storefront ID that does not exist.
    #              Should return None without crashing.
    # ----------------------------------------------------------
    subsection("TEST 1.8 — update_storefront: nonexistent storefront ID")
    result = update_storefront(storefront_id=999999999, bio="ghost")
    check("Returns None for nonexistent ID", result is None)

    # ----------------------------------------------------------
    # TEST 1.9 — set_storefront_active (deactivate)
    # Description: Soft-deactivates a storefront by setting is_active = False.
    #              Validates the flag changed and updated_at was refreshed.
    # ----------------------------------------------------------
    subsection("TEST 1.9 — set_storefront_active: deactivate (False)")
    deactivated = set_storefront_active(storefront_id, False)
    check("Returns updated dict", deactivated is not None)
    check("is_active is now False", deactivated["is_active"] is False)
    check("updated_at is not None", deactivated["updated_at"] is not None)

    # ----------------------------------------------------------
    # TEST 1.10 — set_storefront_active (reactivate)
    # Description: Re-activates the storefront by setting is_active = True.
    #              Confirms the storefront can be toggled back on.
    # ----------------------------------------------------------
    subsection("TEST 1.10 — set_storefront_active: reactivate (True)")
    reactivated = set_storefront_active(storefront_id, True)
    check("Returns updated dict", reactivated is not None)
    check("is_active is now True", reactivated["is_active"] is True)

    # ----------------------------------------------------------
    # TEST 1.11 — get_all_storefronts
    # Description: Retrieves all storefronts (active + inactive).
    #              Validates it returns a list and includes our test storefront.
    # ----------------------------------------------------------
    subsection("TEST 1.11 — get_all_storefronts: returns all rows")
    all_sf = get_all_storefronts()
    check("Returns a list", isinstance(all_sf, list))
    check("List is not empty", len(all_sf) > 0)
    ids_in_list = [s["id"] for s in all_sf]
    check("Test storefront is in results", storefront_id in ids_in_list)

    # ----------------------------------------------------------
    # TEST 1.12 — get_active_storefronts (deactivated excluded)
    # Description: Deactivates the test storefront, then calls get_active_storefronts.
    #              The deactivated storefront must not appear in results.
    # ----------------------------------------------------------
    subsection("TEST 1.12 — get_active_storefronts: deactivated storefront excluded")
    set_storefront_active(storefront_id, False)
    active_sf = get_active_storefronts()
    active_ids = [s["id"] for s in active_sf]
    check("Deactivated storefront NOT in active list", storefront_id not in active_ids)
    set_storefront_active(storefront_id, True)  # restore for remaining tests

    # ----------------------------------------------------------
    # TEST 1.13 — item_count via LEFT JOIN
    # Description: Inserts a test listing for the storefront, then re-fetches it.
    #              item_count should reflect the number of active listings.
    # ----------------------------------------------------------
    subsection("TEST 1.13 — item_count: reflects active listing count via JOIN")
    cur.execute("""
        INSERT INTO listings (storefront_id, title, price, fulfillment_type, quantity_on_hand, status)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
    """, (storefront_id, "Test Listing Item", 25.00, "IN_STOCK", 10, "ACTIVE"))
    conn.commit()
    listing_id = cur.fetchone()[0]

    sf_with_item = get_storefront_by_id(storefront_id)
    check("item_count is 1 after adding a listing", sf_with_item["item_count"] == 1)

    cur.execute("DELETE FROM listings WHERE id = %s;", (listing_id,))
    conn.commit()

    sf_after_delete = get_storefront_by_id(storefront_id)
    check("item_count returns to 0 after listing removed", sf_after_delete["item_count"] == 0)

    return storefront_id, minimal_owner_id


# ________________________________________________________
# SECTION 2 — DATABASE / SCHEMA CONSTRAINT TESTS
# ________________________________________________________

def run_schema_tests(cur, conn, owner_id):
    section("SECTION 2 — DATABASE / SCHEMA CONSTRAINT TESTS")
    print("  These hit the DB directly to verify the schema enforces rules")
    print("  such as NOT NULL, UNIQUE, and FK constraints.\n")

    # ----------------------------------------------------------
    # TEST 2.1 — owner_id UNIQUE constraint
    # Description: Attempts to insert a second storefront for the same owner_id.
    #              The DB UNIQUE constraint must raise an exception.
    # ----------------------------------------------------------
    subsection("TEST 2.1 — owner_id UNIQUE constraint: no duplicate storefronts")
    raised = False
    try:
        cur.execute(
            "INSERT INTO storefronts (owner_id, brand_name) VALUES (%s, %s);",
            (owner_id, "Duplicate Brand")
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raised = True
    check("Duplicate owner_id raises DB error", raised)

    # ----------------------------------------------------------
    # TEST 2.2 — brand_name NOT NULL constraint
    # Description: Attempts to insert a storefront row without brand_name.
    #              The DB NOT NULL constraint must raise an exception.
    # ----------------------------------------------------------
    subsection("TEST 2.2 — brand_name NOT NULL constraint")
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("vault_null_brand_user", "nullbrand@vault-test.com", "testhash_placeholder", "student")
    )
    conn.commit()
    null_brand_uid = cur.fetchone()[0]

    raised = False
    try:
        cur.execute(
            "INSERT INTO storefronts (owner_id, brand_name) VALUES (%s, NULL);",
            (null_brand_uid,)
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raised = True
    check("NULL brand_name raises DB error", raised)
    cur.execute("DELETE FROM users WHERE id = %s;", (null_brand_uid,))
    conn.commit()

    # ----------------------------------------------------------
    # TEST 2.3 — owner_id FK constraint
    # Description: Attempts to insert a storefront referencing a user_id
    #              that does not exist in the users table.
    #              The FK constraint must reject the insert.
    # ----------------------------------------------------------
    subsection("TEST 2.3 — owner_id FK constraint: must reference valid user")
    raised = False
    try:
        cur.execute(
            "INSERT INTO storefronts (owner_id, brand_name) VALUES (%s, %s);",
            (999999998, "Ghost Brand")
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raised = True
    check("Nonexistent owner_id raises FK error", raised)

    # ----------------------------------------------------------
    # TEST 2.4 — is_active defaults to TRUE
    # Description: Inserts a row without specifying is_active.
    #              The column default must set it to True automatically.
    # ----------------------------------------------------------
    subsection("TEST 2.4 — is_active defaults to TRUE")
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("vault_default_active_user", "defactive@vault-test.com", "testhash_placeholder", "student")
    )
    conn.commit()
    default_uid = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO storefronts (owner_id, brand_name) VALUES (%s, %s) RETURNING is_active;",
        (default_uid, "Default Active Brand")
    )
    conn.commit()
    is_active_val = cur.fetchone()[0]
    check("is_active defaults to True without explicit value", is_active_val is True)
    cur.execute("DELETE FROM storefronts WHERE owner_id = %s;", (default_uid,))
    cur.execute("DELETE FROM users WHERE id = %s;", (default_uid,))
    conn.commit()

    # ----------------------------------------------------------
    # TEST 2.5 — created_at and updated_at auto-set on insert
    # Description: Retrieves timestamps after a new row is inserted.
    #              Both must be non-null and populated by the DB default.
    # ----------------------------------------------------------
    subsection("TEST 2.5 — created_at / updated_at auto-set on insert")
    cur.execute(
        "SELECT created_at, updated_at FROM storefronts WHERE owner_id = %s;",
        (owner_id,)
    )
    row = cur.fetchone()
    check("created_at is not None", row is not None and row[0] is not None)
    check("updated_at is not None", row is not None and row[1] is not None)


# ________________________________________________________
# SECTION 3 — SERVICE LAYER TESTS
# ________________________________________________________

def run_service_tests(cur, conn, owner_id, storefront_id):
    section("SECTION 3 — SERVICE LAYER TESTS")
    print("  These test storefront_service.py: business rules, validation,")
    print("  permission checks, and ownership enforcement.\n")

    owner_user  = {"id": owner_id, "role": "student"}
    admin_user  = {"id": 0,        "role": "admin"}
    other_user  = {"id": 999999997,"role": "student"}

    # ----------------------------------------------------------
    # TEST 3.1 — create_storefront_service (success)
    # Description: Creates a new storefront through the service layer.
    #              Validates the returned dict and that the row exists in the DB.
    # ----------------------------------------------------------
    subsection("TEST 3.1 — create_storefront_service: success (new user)")
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("vault_svc_user", "svcuser@vault-test.com", "testhash_placeholder", "student")
    )
    conn.commit()
    svc_uid = cur.fetchone()[0]
    svc_user = {"id": svc_uid, "role": "student"}

    result = create_storefront_service(svc_user, {"brand_name": "Service Test Brand", "bio": "Hello"})
    check("Returns storefront dict", isinstance(result, dict))
    check("brand_name saved correctly", result["brand_name"] == "Service Test Brand")
    db_check = get_storefront_by_owner_id(svc_uid)
    check("Row exists in DB after service create", db_check is not None)

    # ----------------------------------------------------------
    # TEST 3.2 — create_storefront_service (no user — unauthorized)
    # Description: Passes None as current_user.
    #              Service must raise an "Unauthorized" exception.
    # ----------------------------------------------------------
    subsection("TEST 3.2 — create_storefront_service: no user (unauthorized)")
    raised_msg = ""
    try:
        create_storefront_service(None, {"brand_name": "Ghost Brand"})
    except Exception as e:
        raised_msg = str(e)
    check("Raises exception for no user", "Unauthorized" in raised_msg or len(raised_msg) > 0)

    # ----------------------------------------------------------
    # TEST 3.3 — create_storefront_service (duplicate storefront)
    # Description: Attempts to create a second storefront for a user who already has one.
    #              Service must raise "Storefront already created".
    # ----------------------------------------------------------
    subsection("TEST 3.3 — create_storefront_service: duplicate storefront rejected")
    raised_msg = ""
    try:
        create_storefront_service(owner_user, {"brand_name": "Second Brand"})
    except Exception as e:
        raised_msg = str(e)
    check("Raises 'already created' error", "already" in raised_msg.lower())

    # ----------------------------------------------------------
    # TEST 3.4 — create_storefront_service (missing brand_name)
    # Description: Passes an empty data dict with no brand_name key.
    #              Service must raise "brand_name is required".
    # ----------------------------------------------------------
    subsection("TEST 3.4 — create_storefront_service: missing brand_name rejected")
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("vault_nobrand_user", "nobrand@vault-test.com", "testhash_placeholder", "student")
    )
    conn.commit()
    nobrand_uid = cur.fetchone()[0]
    raised_msg = ""
    try:
        create_storefront_service({"id": nobrand_uid, "role": "student"}, {})
    except Exception as e:
        raised_msg = str(e)
    check("Raises 'brand_name is required' error", "brand_name" in raised_msg.lower())
    cur.execute("DELETE FROM users WHERE id = %s;", (nobrand_uid,))
    conn.commit()

    # ----------------------------------------------------------
    # TEST 3.5 — create_storefront_service (blank brand_name whitespace)
    # Description: Passes brand_name as "   " (whitespace only).
    #              The strip() check in the service must reject it.
    # ----------------------------------------------------------
    subsection("TEST 3.5 — create_storefront_service: whitespace-only brand_name rejected")
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("vault_blankbrand_user", "blank@vault-test.com", "testhash_placeholder", "student")
    )
    conn.commit()
    blank_uid = cur.fetchone()[0]
    raised_msg = ""
    try:
        create_storefront_service({"id": blank_uid, "role": "student"}, {"brand_name": "   "})
    except Exception as e:
        raised_msg = str(e)
    check("Raises error for whitespace brand_name", "brand_name" in raised_msg.lower())
    cur.execute("DELETE FROM users WHERE id = %s;", (blank_uid,))
    conn.commit()

    # ----------------------------------------------------------
    # TEST 3.6 — get_my_storefront_service (success)
    # Description: Retrieves the authenticated user's own storefront via the service.
    #              Validates the returned storefront belongs to the correct owner.
    # ----------------------------------------------------------
    subsection("TEST 3.6 — get_my_storefront_service: returns correct storefront")
    my_sf = get_my_storefront_service(owner_user)
    check("Returns a dict (not None)", my_sf is not None)
    check("owner_id matches current user", my_sf["owner_id"] == owner_id)

    # ----------------------------------------------------------
    # TEST 3.7 — get_my_storefront_service (no user)
    # Description: Passes None as current_user.
    #              Service must raise an "Unauthorized" exception.
    # ----------------------------------------------------------
    subsection("TEST 3.7 — get_my_storefront_service: no user (unauthorized)")
    raised_msg = ""
    try:
        get_my_storefront_service(None)
    except Exception as e:
        raised_msg = str(e)
    check("Raises exception for no user", len(raised_msg) > 0)

    # ----------------------------------------------------------
    # TEST 3.8 — update_storefront_service (owner updates own storefront)
    # Description: Owner updates bio and contact_info on their own storefront.
    #              Validates returned dict reflects new values.
    # ----------------------------------------------------------
    subsection("TEST 3.8 — update_storefront_service: owner can update their storefront")
    updated = update_storefront_service(
        owner_user, storefront_id,
        {"bio": "Updated via service", "contact_info": "owner@hampton.edu"}
    )
    check("Returns updated dict", updated is not None)
    check("bio updated", updated["bio"] == "Updated via service")
    check("contact_info updated", updated["contact_info"] == "owner@hampton.edu")

    # ----------------------------------------------------------
    # TEST 3.9 — update_storefront_service (admin updates any storefront)
    # Description: An admin user updates a storefront they do not own.
    #              Service must allow the update (admin bypass).
    # ----------------------------------------------------------
    subsection("TEST 3.9 — update_storefront_service: admin can update any storefront")
    admin_update = update_storefront_service(
        admin_user, storefront_id,
        {"bio": "Admin override bio"}
    )
    check("Admin update returns dict", admin_update is not None)
    check("bio updated by admin", admin_update["bio"] == "Admin override bio")

    # ----------------------------------------------------------
    # TEST 3.10 — update_storefront_service (wrong user — unauthorized)
    # Description: A different non-admin user attempts to update someone else's storefront.
    #              Service must raise "Unauthorized action".
    # ----------------------------------------------------------
    subsection("TEST 3.10 — update_storefront_service: non-owner rejected")
    raised_msg = ""
    try:
        update_storefront_service(other_user, storefront_id, {"bio": "Hacked bio"})
    except Exception as e:
        raised_msg = str(e)
    check("Raises 'Unauthorized' error for non-owner", "unauthorized" in raised_msg.lower())

    # ----------------------------------------------------------
    # TEST 3.11 — update_storefront_service (blank brand_name)
    # Description: Owner attempts to update brand_name to an empty string.
    #              Service must raise "brand_name cannot be empty".
    # ----------------------------------------------------------
    subsection("TEST 3.11 — update_storefront_service: blank brand_name rejected")
    raised_msg = ""
    try:
        update_storefront_service(owner_user, storefront_id, {"brand_name": "   "})
    except Exception as e:
        raised_msg = str(e)
    check("Raises error for blank brand_name on update", "brand_name" in raised_msg.lower())

    # ----------------------------------------------------------
    # TEST 3.12 — update_storefront_service (storefront not found)
    # Description: Attempts to update a storefront ID that does not exist.
    #              Service must raise "Storefront not found".
    # ----------------------------------------------------------
    subsection("TEST 3.12 — update_storefront_service: storefront not found")
    raised_msg = ""
    try:
        update_storefront_service(owner_user, 999999999, {"bio": "ghost"})
    except Exception as e:
        raised_msg = str(e)
    check("Raises 'not found' error", "not found" in raised_msg.lower())

    # ----------------------------------------------------------
    # TEST 3.13 — update_storefront_service (preview images passthrough)
    # Description: Updates all 4 preview image URLs via the service.
    #              Validates every preview_image_1-4 field is stored and returned correctly.
    # ----------------------------------------------------------
    subsection("TEST 3.13 — update_storefront_service: all 4 preview images stored correctly")
    preview_update = update_storefront_service(owner_user, storefront_id, {
        "preview_image_1": "https://s3.example.com/svc_p1.png",
        "preview_image_2": "https://s3.example.com/svc_p2.png",
        "preview_image_3": "https://s3.example.com/svc_p3.png",
        "preview_image_4": "https://s3.example.com/svc_p4.png",
    })
    check("preview_image_1 stored correctly", preview_update["preview_image_1"] == "https://s3.example.com/svc_p1.png")
    check("preview_image_2 stored correctly", preview_update["preview_image_2"] == "https://s3.example.com/svc_p2.png")
    check("preview_image_3 stored correctly", preview_update["preview_image_3"] == "https://s3.example.com/svc_p3.png")
    check("preview_image_4 stored correctly", preview_update["preview_image_4"] == "https://s3.example.com/svc_p4.png")

    # ----------------------------------------------------------
    # TEST 3.14 — deactivate_storefront_service (owner deactivates)
    # Description: Owner deactivates their own storefront.
    #              Validates is_active becomes False in the returned dict.
    # ----------------------------------------------------------
    subsection("TEST 3.14 — deactivate_storefront_service: owner can deactivate")
    result = deactivate_storefront_service(owner_user, storefront_id)
    check("Returns dict after deactivation", result is not None)
    check("is_active is False", result["is_active"] is False)
    set_storefront_active(storefront_id, True)  # restore

    # ----------------------------------------------------------
    # TEST 3.15 — deactivate_storefront_service (admin deactivates any)
    # Description: Admin deactivates a storefront they do not own.
    #              Service must allow it (admin bypass).
    # ----------------------------------------------------------
    subsection("TEST 3.15 — deactivate_storefront_service: admin can deactivate any")
    result = deactivate_storefront_service(admin_user, storefront_id)
    check("Admin deactivation returns dict", result is not None)
    check("is_active is False after admin deactivate", result["is_active"] is False)
    set_storefront_active(storefront_id, True)  # restore

    # ----------------------------------------------------------
    # TEST 3.16 — deactivate_storefront_service (unauthorized user)
    # Description: A non-owner, non-admin user attempts to deactivate someone else's storefront.
    #              Service must raise "Unauthorized action".
    # ----------------------------------------------------------
    subsection("TEST 3.16 — deactivate_storefront_service: non-owner rejected")
    raised_msg = ""
    try:
        deactivate_storefront_service(other_user, storefront_id)
    except Exception as e:
        raised_msg = str(e)
    check("Raises 'Unauthorized' error for non-owner", "unauthorized" in raised_msg.lower())

    # ----------------------------------------------------------
    # TEST 3.17 — deactivate_storefront_service (storefront not found)
    # Description: Attempts to deactivate a storefront ID that does not exist.
    #              Service must raise "Storefront not found".
    # ----------------------------------------------------------
    subsection("TEST 3.17 — deactivate_storefront_service: storefront not found")
    raised_msg = ""
    try:
        deactivate_storefront_service(owner_user, 999999999)
    except Exception as e:
        raised_msg = str(e)
    check("Raises 'not found' error", "not found" in raised_msg.lower())

    return svc_uid


# ________________________________________________________
# SECTION 4 — API / ROUTE TESTS (Flask Test Client)
# ________________________________________________________

def run_api_tests(owner_id, storefront_id):
    section("SECTION 4 — API / ROUTE TESTS (Flask Test Client)")
    print("  These send real HTTP requests through the Flask app and check")
    print("  response status codes and JSON payloads.\n")

    try:
        import app as flask_app
        client = flask_app.app.test_client()
        flask_app.app.config["TESTING"] = True
    except Exception as e:
        print(f"  [SKIP] Could not load Flask app for API tests: {e}")
        return

    auth_headers = {
        "X-User-Id": str(owner_id),
        "X-User-Role": "student"
    }
    admin_headers = {
        "X-User-Id": "0",
        "X-User-Role": "admin"
    }

    # ----------------------------------------------------------
    # TEST 4.1 — GET /api/storefronts (all storefronts)
    # Description: Fetches the full list of active storefronts.
    #              Expects 200 and a JSON list in the response.
    # ----------------------------------------------------------
    subsection("TEST 4.1 — GET /api/storefronts: returns storefront list")
    res = client.get("/api/storefronts")
    check("Status 200", res.status_code == 200)
    data = res.get_json()
    check("Response is a list", isinstance(data, list))

    # ----------------------------------------------------------
    # TEST 4.2 — GET /api/storefronts/<id> (valid ID)
    # Description: Fetches a specific storefront by ID.
    #              Expects 200 and the correct storefront JSON.
    # ----------------------------------------------------------
    subsection("TEST 4.2 — GET /api/storefronts/<id>: valid storefront returned")
    res = client.get(f"/api/storefronts/{storefront_id}")
    check("Status 200", res.status_code == 200)
    data = res.get_json()
    check("Correct storefront ID in response", data.get("id") == storefront_id)

    # ----------------------------------------------------------
    # TEST 4.3 — GET /api/storefronts/<id> (invalid ID)
    # Description: Requests a storefront that does not exist.
    #              Expects a 404 response.
    # ----------------------------------------------------------
    subsection("TEST 4.3 — GET /api/storefronts/<id>: nonexistent ID returns 404")
    res = client.get("/api/storefronts/999999999")
    check("Status 404", res.status_code == 404)

    # ----------------------------------------------------------
    # TEST 4.4 — POST /api/storefronts (authenticated, new user)
    # Description: Creates a storefront via the API route with valid auth headers.
    #              Expects 201 and the new storefront in the response.
    # ----------------------------------------------------------
    subsection("TEST 4.4 — POST /api/storefronts: authenticated user creates storefront")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("vault_api_create_user", "apicreate@vault-test.com", "testhash_placeholder", "student")
    )
    conn.commit()
    api_create_uid = cur.fetchone()[0]
    cur.close()
    conn.close()

    res = client.post("/api/storefronts",
        json={"brand_name": "API Created Brand"},
        headers={"X-User-Id": str(api_create_uid), "X-User-Role": "student"},
        content_type="application/json"
    )
    check("Status 201", res.status_code == 201)
    data = res.get_json()
    check("brand_name in response", data.get("brand_name") == "API Created Brand")

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM storefronts WHERE owner_id = %s;", (api_create_uid,))
    cur.execute("DELETE FROM users WHERE id = %s;", (api_create_uid,))
    conn.commit()
    cur.close()
    conn.close()

    # ----------------------------------------------------------
    # TEST 4.5 — POST /api/storefronts (no auth headers)
    # Description: Sends a create request without any auth headers.
    #              Expects a 401 Unauthorized response.
    # ----------------------------------------------------------
    subsection("TEST 4.5 — POST /api/storefronts: no auth headers returns 401")
    res = client.post("/api/storefronts",
        json={"brand_name": "No Auth Brand"},
        content_type="application/json"
    )
    check("Status 401", res.status_code == 401)

    # ----------------------------------------------------------
    # TEST 4.6 — POST /api/storefronts (missing brand_name)
    # Description: Sends a create request with valid auth but no brand_name.
    #              Expects a 400 Bad Request response.
    # ----------------------------------------------------------
    subsection("TEST 4.6 — POST /api/storefronts: missing brand_name returns 400")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s) RETURNING id;",
        ("vault_api_nobrand", "apinobrand@vault-test.com", "testhash_placeholder", "student")
    )
    conn.commit()
    nobrand_api_uid = cur.fetchone()[0]
    cur.close()
    conn.close()

    res = client.post("/api/storefronts",
        json={},
        headers={"X-User-Id": str(nobrand_api_uid), "X-User-Role": "student"},
        content_type="application/json"
    )
    check("Status 400", res.status_code == 400)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE id = %s;", (nobrand_api_uid,))
    conn.commit()
    cur.close()
    conn.close()

    # ----------------------------------------------------------
    # TEST 4.7 — GET /api/storefronts/me (authenticated)
    # Description: Fetches the current user's own storefront via /me route.
    #              Expects 200 and a storefront owned by that user.
    # ----------------------------------------------------------
    subsection("TEST 4.7 — GET /api/storefronts/me: authenticated returns own storefront")
    res = client.get("/api/storefronts/me", headers=auth_headers)
    check("Status 200", res.status_code == 200)
    data = res.get_json()
    check("owner_id matches authenticated user", data.get("owner_id") == owner_id)

    # ----------------------------------------------------------
    # TEST 4.8 — GET /api/storefronts/me (no auth)
    # Description: Requests /me without any auth headers.
    #              Expects a 401 Unauthorized response.
    # ----------------------------------------------------------
    subsection("TEST 4.8 — GET /api/storefronts/me: no auth returns 401")
    res = client.get("/api/storefronts/me")
    check("Status 401", res.status_code == 401)

    # ----------------------------------------------------------
    # TEST 4.9 — PUT /api/storefronts/<id> (owner updates)
    # Description: Owner sends a PUT request to update their own storefront bio.
    #              Expects 200 and updated field in the response JSON.
    # ----------------------------------------------------------
    subsection("TEST 4.9 — PUT /api/storefronts/<id>: owner update returns 200")
    res = client.put(f"/api/storefronts/{storefront_id}",
        json={"bio": "API updated bio"},
        headers=auth_headers,
        content_type="application/json"
    )
    check("Status 200", res.status_code == 200)
    data = res.get_json()
    check("bio updated in response", data.get("bio") == "API updated bio")

    # ----------------------------------------------------------
    # TEST 4.10 — PUT /api/storefronts/<id> (wrong user — unauthorized)
    # Description: A different user sends a PUT request to update someone else's storefront.
    #              Expects a 403 Forbidden response.
    # ----------------------------------------------------------
    subsection("TEST 4.10 — PUT /api/storefronts/<id>: non-owner returns 403")
    wrong_headers = {"X-User-Id": "999999997", "X-User-Role": "student"}
    res = client.put(f"/api/storefronts/{storefront_id}",
        json={"bio": "Hacked bio"},
        headers=wrong_headers,
        content_type="application/json"
    )
    check("Status 403", res.status_code == 403)

    # ----------------------------------------------------------
    # TEST 4.11 — PATCH /api/storefronts/<id>/deactivate (owner)
    # Description: Owner deactivates their storefront via the API route.
    #              Expects 200 and is_active = False in the response.
    # ----------------------------------------------------------
    subsection("TEST 4.11 — PATCH /api/storefronts/<id>/deactivate: owner deactivates")
    res = client.patch(f"/api/storefronts/{storefront_id}/deactivate", headers=auth_headers)
    check("Status 200", res.status_code == 200)
    data = res.get_json()
    check("is_active is False in response", data.get("is_active") is False)
    set_storefront_active(storefront_id, True)  # restore

    # ----------------------------------------------------------
    # TEST 4.12 — PATCH /api/storefronts/<id>/deactivate (unauthorized)
    # Description: A non-owner, non-admin user attempts to deactivate via the API.
    #              Expects a 403 Forbidden response.
    # ----------------------------------------------------------
    subsection("TEST 4.12 — PATCH /api/storefronts/<id>/deactivate: non-owner returns 403")
    wrong_headers = {"X-User-Id": "999999997", "X-User-Role": "student"}
    res = client.patch(f"/api/storefronts/{storefront_id}/deactivate", headers=wrong_headers)
    check("Status 403", res.status_code == 403)


# ________________________________________________________
# MAIN DRIVER
# ________________________________________________________

def run_all_storefront_tests():
    print("\n" + "=" * 60)
    print("  THE VAULT — STOREFRONT TEST DRIVER")
    print("  Created by Day Ekoi | Iteration 5 | 4/20/26")
    print("  Testing: Model Layer, Schema Constraints,")
    print("           Service Layer, API Routes")
    print("=" * 60)

    conn = get_connection()
    if not conn:
        print("\nFATAL: Could not connect to AWS RDS. Aborting all tests.")
        return

    cur = conn.cursor()
    cleanup_ids = []

    # Pre-run cleanup: remove any leftover test data from a previously crashed run
    stale_usernames = [
        "vault_storefront_test_owner", "vault_minimal_user", "vault_no_store_user",
        "vault_null_brand_user", "vault_default_active_user", "vault_svc_user",
        "vault_nobrand_user", "vault_blankbrand_user", "vault_api_create_user",
        "vault_api_nobrand",
    ]
    for uname in stale_usernames:
        cur.execute("DELETE FROM storefronts WHERE owner_id = (SELECT id FROM users WHERE username = %s);", (uname,))
        cur.execute("DELETE FROM users WHERE username = %s;", (uname,))
    conn.commit()

    try:
        # Create primary test user
        owner_id = create_test_user(cur, conn, "vault_storefront_test_owner")
        cleanup_ids.append(owner_id)

        # Section 1 — Model layer
        storefront_id, minimal_owner_id = run_model_tests(cur, conn, owner_id)
        cleanup_ids.append(minimal_owner_id)

        # Section 2 — Schema constraints
        run_schema_tests(cur, conn, owner_id)

        # Section 3 — Service layer
        svc_uid = run_service_tests(cur, conn, owner_id, storefront_id)
        cleanup_ids.append(svc_uid)

        # Section 4 — API routes
        run_api_tests(owner_id, storefront_id)

    except Exception as e:
        print(f"\n[DRIVER ERROR] Unexpected failure: {e}")

    finally:
        conn.rollback()  # clear any aborted transaction before printing or cleanup
        print_db_state(cur)
        print("\n" + "=" * 60)
        print("  CLEANUP — Removing all test data from DB")
        print("=" * 60)
        cleanup(cur, conn, cleanup_ids)
        cur.close()
        conn.close()
        print("  Cleanup complete.\n")

        print("=" * 60)
        print(f"  RESULTS: {passed} passed | {failed} failed | {passed + failed} total")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    run_all_storefront_tests()
