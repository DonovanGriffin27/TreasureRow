# backend/tests/test_browse.py
# Added by Cameron Ridgley - 10/27/26
#
# Discover pages under "More" in the slide-out menu (Explore Brands,
# All Categories, New Drops, Hot!) and GET /api/browse/listings.
#
# Most tests swap the database query for a stub, so they run without a
# database. test_public_listings_query_* uses the TEST database (see
# conftest.py) and is skipped when that database can't be reached.

import uuid

import pytest

import services.browse_service as browse_service
from app import create_app
from db import get_connection
from helpers import create_seller, create_user, delete_users, sign_in

PAGES = {
    "/explore-brands": "Explore Brands",
    "/categories": "All Categories",
    "/new-drops": "New Drops",
    "/hot": "Hot!",
}

FAKE_USER = {"username": "t_browse", "user_id": 1}


@pytest.fixture(scope="module")
def app():
    app = create_app()
    app.config.update(TESTING=True)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def stub_listings(monkeypatch):
    """Replace the SQL query; records the arguments it was called with."""
    calls = []

    def fake_get_public_listings(sort="new", limit=60):
        calls.append({"sort": sort, "limit": limit})
        return [{"id": 1, "title": "Hoodie", "price": 40.0}]

    monkeypatch.setattr(browse_service, "get_public_listings", fake_get_public_listings)
    return calls


# ---------- Pages ----------

@pytest.mark.parametrize("path", PAGES)
def test_pages_require_sign_in(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


@pytest.mark.parametrize("path,title", PAGES.items())
def test_pages_render_for_signed_in_user(client, path, title):
    sign_in(client, FAKE_USER)
    response = client.get(path)
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert f"Treasure Row | {title}" in html
    assert "js/browse_common.js" in html


def test_menu_has_dropdowns_and_discover_links(client):
    sign_in(client, FAKE_USER)
    html = client.get("/new-drops").get_data(as_text=True)
    assert html.count('class="tr-nav-toggle"') == 3          # Shop, Sell, and More
    for path in PAGES:
        assert f'href="{path}"' in html
    assert 'class="tr-nav-link current" href="/new-drops"' in html


def test_shop_dropdown_starts_open_on_shop_pages(client):
    sign_in(client, FAKE_USER)
    html = client.get("/returns").get_data(as_text=True)
    assert 'tr-nav-dropdown open' in html
    assert 'aria-controls="trNavShop"' in html


@pytest.mark.parametrize("path", PAGES)
def test_more_dropdown_starts_open_on_more_pages(client, path):
    sign_in(client, FAKE_USER)
    html = client.get(path).get_data(as_text=True)
    more = html.split('aria-controls="trNavMore"')[0].rsplit("<div", 1)[1]
    assert "tr-nav-dropdown open" in more


@pytest.mark.parametrize("path", ["/returns", "/about", "/sitemap"])
def test_more_dropdown_starts_closed_elsewhere(client, path):
    sign_in(client, FAKE_USER)
    html = client.get(path).get_data(as_text=True)
    more = html.split('aria-controls="trNavMore"')[0].rsplit("<div", 1)[1]
    assert "tr-nav-dropdown open" not in more


def test_account_about_sitemap_and_log_out_sit_outside_more(client):
    sign_in(client, FAKE_USER)
    html = client.get("/returns").get_data(as_text=True)
    more_links = html.split('id="trNavMore"')[1].split("</div></div>")[0]
    after_more = html.split('id="trNavMore"')[1].split("</div></div>", 1)[1].split("</aside>")[0]
    for label in ("My Account", "Messages", "About", "Sitemap", "Log Out"):
        assert label not in more_links
        assert label in after_more


def test_sitemap_lists_discover_pages(client):
    sign_in(client, FAKE_USER)
    html = client.get("/sitemap").get_data(as_text=True)
    for path in PAGES:
        assert f'href="{path}"' in html


# ---------- GET /api/browse/listings ----------

def test_listings_api_requires_sign_in(client, stub_listings):
    response = client.get("/api/browse/listings")
    assert response.status_code == 401
    assert stub_listings == []


def test_listings_api_defaults_to_newest(client, stub_listings):
    sign_in(client, FAKE_USER)
    response = client.get("/api/browse/listings")
    assert response.status_code == 200
    assert response.get_json()[0]["title"] == "Hoodie"
    assert stub_listings == [{"sort": "new", "limit": browse_service.DEFAULT_LIMIT}]


def test_listings_api_hot_sort(client, stub_listings):
    sign_in(client, FAKE_USER)
    assert client.get("/api/browse/listings?sort=HOT&limit=10").status_code == 200
    assert stub_listings == [{"sort": "hot", "limit": 10}]


@pytest.mark.parametrize("raw,expected", [("0", 1), ("-5", 1), ("500", browse_service.MAX_LIMIT)])
def test_listings_api_limit_is_kept_in_range(client, stub_listings, raw, expected):
    sign_in(client, FAKE_USER)
    assert client.get(f"/api/browse/listings?limit={raw}").status_code == 200
    assert stub_listings[-1]["limit"] == expected


@pytest.mark.parametrize("query", ["sort=price; DROP TABLE listings", "limit=ten"])
def test_listings_api_rejects_bad_input(client, stub_listings, query):
    sign_in(client, FAKE_USER)
    response = client.get(f"/api/browse/listings?{query}")
    assert response.status_code == 400
    assert stub_listings == []


def test_popularity_weights_sold_3_saves_2():
    from models.browse_model import SAVE_WEIGHT, SOLD_WEIGHT

    assert (SOLD_WEIGHT, SAVE_WEIGHT) == (3, 2)
    assert 1 * SOLD_WEIGHT + 1 * SAVE_WEIGHT == 5


# ---------- SQL query (TEST database) ----------

@pytest.fixture
def db_people():
    try:
        conn = get_connection()
    except Exception as exc:
        pytest.skip(f"test database not reachable: {exc}")
    cur = conn.cursor()
    popular = create_seller(cur, "bhot")
    saved = create_seller(cur, "bsave")
    hidden = create_seller(cur, "bhide")
    buyer = create_user(cur, "bbuyer")

    # popular: 2 units sold (score 6); saved: 1 wishlist save (score 2)
    cur.execute(
        """INSERT INTO orders (user_id, confirmation_number, buyer_first_name, buyer_last_name,
                               buyer_email, buyer_contact, buyer_meeting_location, total_amount)
           VALUES (%s, %s, 'Test', 'Buyer', 'b@my.hamptonu.edu', '555', 'Student Center', 20)
           RETURNING id;""",
        (buyer["user_id"], f"T-{uuid.uuid4().hex[:10]}"),
    )
    order_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO order_items (order_id, listing_id, item_name, quantity, price_at_purchase) VALUES (%s, %s, 'x', 2, 10);",
        (order_id, popular["listing_id"]),
    )
    cur.execute("INSERT INTO wishlist (user_id, listing_id) VALUES (%s, %s);", (buyer["user_id"], saved["listing_id"]))
    # hidden: storefront deactivated, so its listing must not appear
    cur.execute("UPDATE storefronts SET is_active = FALSE WHERE id = %s;", (hidden["storefront_id"],))
    conn.commit()
    cur.close()
    conn.close()

    yield popular, saved, hidden

    delete_users([buyer["user_id"], popular["user_id"], saved["user_id"], hidden["user_id"]])


def test_public_listings_query_ranks_and_filters(db_people):
    from models.browse_model import get_public_listings

    popular, saved, hidden = db_people
    ours = {popular["listing_id"], saved["listing_id"], hidden["listing_id"]}

    hot = [row for row in get_public_listings("hot", 100) if row["id"] in ours]
    assert [row["id"] for row in hot] == [popular["listing_id"], saved["listing_id"]]
    assert hot[0]["units_sold"] == 2 and hot[0]["popularity"] == 6
    assert hot[1]["wishlist_count"] == 1 and hot[1]["popularity"] == 2
    assert hot[0]["brand_name"].startswith("Brand ")

    new = [row["id"] for row in get_public_listings("new", 100) if row["id"] in ours]
    assert hidden["listing_id"] not in new
    assert set(new) == {popular["listing_id"], saved["listing_id"]}
