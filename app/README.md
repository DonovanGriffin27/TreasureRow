# Treasure Row — Campus Marketplace

**A cloud-based fashion marketplace for Hampton University students**

CSC 404 — Fall 26'. Built on The Vault (CSC 405, Spring 2026).

---

## Live Deployment

Being redeployed to AWS Elastic Beanstalk in Iteration 3 — the URL will be added here.

---

## What is Treasure Row?

Treasure Row is a web-based campus marketplace exclusively for Hampton University students. It allows student brand owners to create storefronts, publish clothing listings, and manage inventory, while other students can browse, wishlist, and purchase items.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | PostgreSQL (AWS RDS) |
| Image Storage | Amazon S3 |
| Cloud Hosting | AWS Elastic Beanstalk |
| DB Adapter | psycopg2 |
| Version Control | GitHub |

---

## Setup & Running Locally

### Prerequisites
- Python 3.12+
- AWS RDS credentials (or a local PostgreSQL database)
- AWS credentials for S3 (optional — without them, uploads are saved under `static/uploads/`)

### Installation

```bash
git clone git@github.com:DonovanGriffin27/TreasureRow.git
cd TreasureRow/app

python3 -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### Environment Configuration

Copy `.env.example` to `.env` in this folder and fill in real values (never commit `.env`).
The app will not start without `SECRET_KEY`. Generate one with:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

On Elastic Beanstalk, set the same variables as **environment properties** instead of a `.env` file.
Set `SESSION_COOKIE_SECURE=1` once the site is served over HTTPS.

### Initialize the Database

```bash
python3 backend/init_db.py
```

### Run the App

```bash
flask --app app run --debug --port 5001
```

Visit `http://127.0.0.1:5001` in your browser. (Port 5001, not 5000: on macOS,
AirPlay Receiver already uses port 5000 and answers with a blank page.)

Everything except the landing page, Sign In, Create Account, and Admin sign-in
requires a signed-in user.

---

## Running Tests

The tests create and delete real users, storefronts, listings, and orders, so they
run against a **separate local test database** - never the team's AWS database
(`backend/tests/conftest.py` refuses to run if `DB_HOST` is an AWS address).

One-time setup:

```bash
createdb treasurerow_test
cp .env.test.example .env.test   # then set DB_USER / DB_PASSWORD for your machine
```

Run the whole suite from `app/app`:

```bash
python3 -m pytest backend/tests
```

| Test file | Covers |
|---|---|
| `test_ownership.py` | account ownership bug: account switching, direct API calls, spoofed identity headers |
| `test_cart_pricing.py` | prices and quantities always come from the database, not the browser |
| `test_uploads.py` | uploads must be real images, in allowed folders, under the size limit |
| `test_hardening.py` | CSRF protection, returns limited to your own orders, required `SECRET_KEY` |
| `test_checkout.py`, `test_wishlist_feature.py`, `test_create_listing_feature.py`, `test_admin.py`, `test_user.py` | feature behavior |

Uploads made by tests are saved under `static/uploads/` instead of S3.

---

## Team

| Name | Role |
|---|---|
| Donovan Griffin | Project Manager, Testing & QA |
| Jonah Goodwine | Co-PM, Dev Team |
| Cameron Ridgley | Dev Team, Jira board |
| Chase Jones | Docs Team (Requirements) |
| Ricki Davis | Docs Team (Functional Spec) |
| Chi Martin | Docs Team (Design Spec) |
| Noah Higgs | Docs Team (Security & Deployment) |

---

## Notes

- Restricted to Hampton University email addresses (`@hamptonu.edu` / `@my.hamptonu.edu`)
- No payment processing — checkout uses an in-person exchange model
- Hosted on AWS (Elastic Beanstalk, RDS, S3)
