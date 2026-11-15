#!/usr/bin/env bash
# Noah Higgs
# Treasure Row installer for macOS. Safe to run again: it never overwrites an
# existing .env and the database setup only creates what is missing.

set -u
cd "$(dirname "$0")" || exit 1

say()  { printf '\n== %s\n' "$1"; }
fail() { printf '\nERROR: %s\n' "$1" >&2; exit 1; }

say "1/5 Checking for Python 3.12 or newer"
PY=""
for cand in python3.12 python3.13 python3.14 python3; do
  if command -v "$cand" >/dev/null 2>&1 \
     && "$cand" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)' 2>/dev/null; then
    PY="$cand"
    break
  fi
done
[ -n "$PY" ] || fail "Python 3.12 or newer was not found. Install it from https://www.python.org/downloads/ (or run: brew install python@3.12), then run ./install.sh again."
echo "Using $($PY --version)"

say "2/5 Creating the virtual environment and installing requirements"
if [ ! -x venv/bin/python ]; then
  "$PY" -m venv venv || fail "Could not create the virtual environment (venv)."
fi
venv/bin/python -m pip install --quiet --upgrade pip
venv/bin/python -m pip install --quiet -r requirements.txt \
  || fail "Installing the requirements failed. Check your internet connection and run ./install.sh again."
echo "Requirements installed."

say "3/5 Setting up the .env file"
if [ -f .env ]; then
  echo ".env already exists, so it was left as it is."
else
  [ -f .env.example ] || fail ".env.example is missing from this folder."
  venv/bin/python - <<'PY' || fail "Could not create the .env file."
import getpass
import os
import secrets

values = {
    "SECRET_KEY": secrets.token_hex(32),
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": secrets.token_urlsafe(12),
    # Postgres.app and Homebrew Postgres use your Mac username and no password
    "DB_USER": getpass.getuser(),
    "DB_PASSWORD": "",
    # blank mail server: password reset links print in the terminal instead
    "MAIL_SERVER": "",
    "MAIL_USERNAME": "",
    "MAIL_PASSWORD": "",
    "MAIL_FROM": "",
}

lines = []
with open(".env.example", encoding="utf-8") as src:
    for line in src:
        key = line.split("=", 1)[0]
        if "=" in line and not line.startswith("#") and key in values:
            lines.append(f"{key}={values[key]}\n")
        else:
            lines.append(line)

with open(".env", "w", encoding="utf-8") as out:
    out.write("".join(lines))
os.chmod(".env", 0o600)

print("Created .env with a new random secret key.")
print()
print("Admin sign-in for testing (shown once, also saved in .env):")
print("  username: admin")
print("  password: " + values["ADMIN_PASSWORD"])
PY
fi

say "4/5 Checking the local PostgreSQL database"
venv/bin/python - <<'PY'
import os
import sys

import psycopg2
from dotenv import load_dotenv
from psycopg2 import sql

load_dotenv(".env")
name = os.getenv("DB_NAME") or "treasurerow"
kwargs = dict(
    host=os.getenv("DB_HOST") or "localhost",
    port=int(os.getenv("DB_PORT") or 5432),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD") or None,
    connect_timeout=5,
)

try:
    psycopg2.connect(dbname=name, **kwargs).close()
    print(f"Database '{name}' is ready.")
except psycopg2.OperationalError:
    try:
        conn = psycopg2.connect(dbname="postgres", **kwargs)
    except psycopg2.OperationalError as err:
        print("Could not reach PostgreSQL: " + str(err).strip())
        sys.exit(2)
    conn.autocommit = True
    conn.cursor().execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    conn.close()
    print(f"Created database '{name}'.")
PY
if [ $? -ne 0 ]; then
  fail "PostgreSQL is not reachable. Install Postgres.app from https://postgresapp.com, open it and click Start, then run ./install.sh again. If your Postgres has a password, put it in DB_PASSWORD in the .env file first."
fi

say "5/5 Creating the database tables"
OUT=$(venv/bin/python backend/init_db.py 2>&1)
echo "$OUT"
case "$OUT" in
  *"DATABASE INITIALIZED"*) ;;
  *) fail "The database tables were not created. Read the message above, fix it, and run ./install.sh again." ;;
esac

printf '\nAll done. Start Treasure Row by double-clicking "Launch TreasureRow.command"\n'
printf '(or run: ./"Launch TreasureRow.command").\n'
