# Treasure Row — Beta Release (v0.4-beta)

**A campus marketplace for Hampton University students.** Student brand owners open storefronts and list clothing; other students browse, wishlist, and buy, paying with Treasure Tokens held in escrow until an in-person pickup.

CSC 404 — Fall 2026 · Iteration 4

**Live site:** http://treasurerow.us-east-2.elasticbeanstalk.com

---

## Features

- **Accounts:** sign up with a `@my.hamptonu.edu` student email, sign in, sign out
- **Forgot password (new in Iteration 4):** emails a reset link that expires after 30 minutes and works once
- **Change password (new in Iteration 4):** from the Account page
- **Storefronts:** create, edit, deactivate, and reactivate your own store
- **Listings:** create and edit listings with up to 4 photos, sizes, and stock
- **Browse:** Explore Brands, Categories, New Drops, and Hot pages
- **Shopping:** wishlist, bag (cart), checkout, and order confirmation
- **Treasure Tokens:** in-app wallet; payment is held in escrow until pickup
- **Messaging:** buyers and sellers message each other
- **Returns:** request a return on your own orders
- **Admin dashboard:** manage users, listings, storefronts, returns, wallets, and escrow
- **Security:** login lockout and rate limiting, CSRF protection, secure session cookies, hashed passwords

---

## Requirements

| Software | Version | Get it |
|---|---|---|
| Python | 3.12 or newer | https://www.python.org/downloads/ |
| PostgreSQL | 14 or newer | Mac: [Postgres.app](https://postgresapp.com/) · Windows: [PostgreSQL installer](https://www.postgresql.org/download/windows/) |

Install both before running the installer. On Windows, check **"Add Python to PATH"** during the Python install.

---

## Install and Launch (one click)

Download or clone this repository, then open the `app` folder.

### Mac
1. Double-click **`install.sh`**. If macOS blocks it, right-click → **Open** → **Open**.
2. When it finishes, double-click **`Launch TreasureRow.command`**.
3. Your browser opens to **http://127.0.0.1:5001**.

### Windows
1. Double-click **`install.bat`**.
2. When it finishes, double-click **`Launch TreasureRow.bat`**.
3. Your browser opens to **http://127.0.0.1:5001**.

The installer checks your Python version, creates a virtual environment, installs the required packages, creates your `.env` settings file, and sets up the database tables. You only run it once. After that, use the **Launch** file every time.

---

## Manual Install (if the installer doesn't work)

```bash
git clone https://github.com/DonovanGriffin27/TreasureRow.git
cd TreasureRow/app

python3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
```

Open `.env` and set:
- `SECRET_KEY` — any long random value. Generate one with:
  `python3 -c "import secrets; print(secrets.token_hex(32))"`
- `DB_USER` / `DB_PASSWORD` — your local PostgreSQL login

Create the database and tables, then start the app:

```bash
createdb treasurerow
python3 backend/init_db.py
flask --app app run --port 5001
```

Visit **http://127.0.0.1:5001**.

> **Why port 5001?** On macOS, AirPlay Receiver already uses port 5000 and shows a blank page.

---

## Using the App

1. Click **Create an account** and sign up with a `@my.hamptonu.edu` email.
2. Sign in, then browse items from the home page or open a store with **Create Storefront**.
3. Every new account starts with **200 Treasure Tokens** for checkout.

**Admin dashboard:** go to **Administrator sign in** on the login page and use the `ADMIN_USERNAME` and `ADMIN_PASSWORD` from your `.env`.

### Forgot password emails
- **Running locally without email settings:** the reset link prints in the terminal window running the app. Copy it into your browser.
- **To send real emails:** fill in the `MAIL_` settings in `.env` with a Gmail address and a Gmail [App Password](https://myaccount.google.com/apppasswords).

---

## Running the Tests

The tests use a **separate local test database**, never the team's AWS database.

```bash
createdb treasurerow_test
cp .env.test.example .env.test   # then set DB_USER / DB_PASSWORD
python3 -m pytest backend/tests
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `SECRET_KEY is not set` | Set `SECRET_KEY` in `.env` (see Manual Install) |
| "We couldn't reach the database" | Make sure PostgreSQL is running and `DB_USER` / `DB_PASSWORD` in `.env` are correct |
| Blank page on port 5000 | Use **http://127.0.0.1:5001** instead |
| `python3: command not found` (Windows) | Reinstall Python with **"Add Python to PATH"** checked, or use `python` instead of `python3` |
| Mac says the installer "can't be opened" | Right-click the file → **Open** → **Open** |
| Images don't upload to S3 | Leave the `AWS_` settings blank; images save to `static/uploads/` instead |

---

## Known Issues (Beta)

- Payments use Treasure Tokens only; there is no real card processing.
- Rate limits reset when the app restarts.
- Reset emails sent from Gmail may land in the spam folder.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | PostgreSQL (AWS RDS) |
| Image storage | Amazon S3 (local folder fallback) |
| Hosting | AWS Elastic Beanstalk |
| Email | Gmail SMTP |

---

## Repository Layout

```
app/             Treasure Row app (Flask backend, templates, static files)
docs/            Formal deliverables, one folder per document
  requirements/     Requirements Document
  functional-spec/  Functional Specification
  design-spec/      Design Specification
  test-plan/        Test Specification
  risk-assessment/  Risk Assessment
  project-plan/     Project Plan
  aws-runbook/      AWS access, deployment, and shutdown runbook
  meeting-minutes/  Meeting minutes
  time-logs/        Team time logs
presentations/   Slide decks, one per iteration
```

---

## Team

| Name | Role |
|---|---|
| Donovan Griffin | Project Manager |
| Jonah Goodwine | Co-PM, Dev Team |
| Cameron Ridgley | Dev Team |
| Noah Higgs | Security & Deployment |
| Chi Martin | Docs Team (Test Specification) |
| Ricki Davis | Docs Team (Risk Assessment) |
| Chase Jones | Docs Team (Design Spec, Requirements) |

---

## Branches

- `main` — stable release
- `develop` — integration branch; feature work merges here first
- One branch per team member, cut from `develop`. Open a pull request into `develop` and get one review before merging.
