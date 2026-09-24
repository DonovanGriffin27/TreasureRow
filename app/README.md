# The Vault — Campus Marketplace

**A cloud-based fashion marketplace for Hampton University students**

Designed & Built by David Jackson, Elali McNair, Day Ekoi, Ryan Grimes, Kaila Roberts, and Madison Boyd
CSC 405 — Spring 26'

---

## Live Deployment

**http://the-vault-env.eba-a7vun5tm.us-east-2.elasticbeanstalk.com**

---

## What is The Vault?

The Vault is a web-based campus marketplace exclusively for Hampton University students. It allows student brand owners to create storefronts, publish clothing listings, and manage inventory, while other students can browse, wishlist, and purchase items.

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
- AWS RDS credentials
- AWS credentials (for S3 access)

### Installation

```bash
git clone https://github.com/DavidJ46/TheVaultProject.git
cd TheVaultProject

python3 -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

pip install -r requirements.txt
```

### Environment Configuration

Create a `.env` file in the root directory:

DB_HOST=your-aws-rds-endpoint
DB_NAME=your-database-name
DB_USER=your-db-username
DB_PASSWORD=your-db-password
DB_PORT=5432
DB_SSLMODE=require
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-s3-bucket-name
AWS_REGION=us-east-2
SECRET_KEY=your-secret-key

### Initialize the Database

```bash
python3 backend/init_db.py
```

### Run the App

```bash
python3 app.py
```

Visit `http://127.0.0.1:5000` in your browser.

---

## Running Tests

```bash
python3 backend/tests/test_file_name
```

---

## Team

| Name | Role |
|---|---|
| David Jackson | Project Manager, Admin backend & frontend |
| Elali McNair | Co-PM, Wishlist & Purchase backend, Create Listing frontend |
| Ryan Grimes | Systems & Security Lead, Auth backend, Login/Signup/Cart frontend |
| Day Ekoi | Cloud Deployment Lead, Storefront & Listings backend & frontend, Returns system, AWS deployment |
| Madison Boyd | Documentation Lead, User & Account Settings backend & frontend |
| Kaila Roberts | Database & App Support, Checkout backend and frontend |

---

## Notes

- Restricted to Hampton University email addresses (`@hamptonu.edu` / `@my.hamptonu.edu`)
- No payment processing — checkout uses an in-person exchange model
- Deployed on AWS Free Tier