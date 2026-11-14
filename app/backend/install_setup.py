# Jonah Goodwine
# CSC 404 - Fall 26'
# Iteration 4 - Installer setup
#
# Run by install.bat (Windows) after the packages are installed.
# 1. creates .env from .env.example if it doesn't exist yet
# 2. fills in a real SECRET_KEY and admin login so the app can start
# 3. asks for the local PostgreSQL login and checks that it works
# 4. creates the treasurerow database if it doesn't exist yet
# init_db.py runs after this to make the tables.

import os
import secrets
import shutil
import getpass

import psycopg2

APP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ENV_PATH = os.path.join(APP_DIR, ".env")
EXAMPLE_PATH = os.path.join(APP_DIR, ".env.example")
PLACEHOLDER = "change-me"


# reads .env into a list of lines so comments and order are kept
def read_env_lines():
    envFile = open(ENV_PATH, "r", encoding="utf-8")
    lines = envFile.read().splitlines()
    envFile.close()
    return lines


def write_env_lines(lines):
    envFile = open(ENV_PATH, "w", encoding="utf-8")
    envFile.write("\n".join(lines) + "\n")
    envFile.close()


# returns the value for a key, or None if the key isn't in the file
def get_value(lines, key):
    for line in lines:
        if line.startswith(key + "="):
            return line[len(key) + 1:].strip()
    return None


# changes the first uncommented line for a key (adds it if missing)
def set_value(lines, key, value):
    found = False
    for i in range(len(lines)):
        if lines[i].startswith(key + "="):
            lines[i] = key + "=" + value
            found = True
            break
    if not found:
        lines.append(key + "=" + value)


def is_unset(value):
    return value is None or value == "" or value == PLACEHOLDER


def try_connect(dbName, user, password, host, port):
    try:
        conn = psycopg2.connect(dbname=dbName, user=user, password=password,
                                host=host, port=port, connect_timeout=5)
        return conn, None
    except psycopg2.OperationalError as e:
        return None, str(e).strip().splitlines()[0]  # first line is enough


def main():
    # step 1 - make .env
    if not os.path.exists(ENV_PATH):
        shutil.copyfile(EXAMPLE_PATH, ENV_PATH)
        print("Created .env from .env.example")
    else:
        print("Found existing .env - keeping your settings")

    lines = read_env_lines()

    # step 2 - secret key and admin login
    if is_unset(get_value(lines, "SECRET_KEY")):
        set_value(lines, "SECRET_KEY", secrets.token_hex(32))
        print("Generated a new SECRET_KEY")

    if is_unset(get_value(lines, "ADMIN_USERNAME")):
        set_value(lines, "ADMIN_USERNAME", "admin")

    adminPassword = get_value(lines, "ADMIN_PASSWORD")
    if is_unset(adminPassword):
        adminPassword = secrets.token_urlsafe(9)
        set_value(lines, "ADMIN_PASSWORD", adminPassword)

    # no Gmail settings locally - reset links print in the app window instead
    if get_value(lines, "MAIL_USERNAME") in (None, "", PLACEHOLDER + "@gmail.com"):
        set_value(lines, "MAIL_SERVER", "")

    # step 3 - local database login
    host = get_value(lines, "DB_HOST") or "localhost"
    if "amazonaws.com" in host:
        # someone pointed .env at the team database - the installer only sets up local
        print("DB_HOST points at AWS - skipping local database setup")
        write_env_lines(lines)
        return

    port = get_value(lines, "DB_PORT") or "5432"
    dbName = get_value(lines, "DB_NAME") or "treasurerow"
    user = get_value(lines, "DB_USER") or "postgres"
    password = get_value(lines, "DB_PASSWORD")
    if password == PLACEHOLDER:
        password = None

    conn = None
    attempts = 0
    while conn is None and attempts < 3:
        if password is None:
            typed = input("PostgreSQL username [" + user + "]: ").strip()
            if typed != "":
                user = typed
            password = getpass.getpass("PostgreSQL password (the one you set when installing PostgreSQL): ")
        # connect to the built-in postgres database first, ours may not exist yet
        conn, error = try_connect("postgres", user, password, host, port)
        if conn is None:
            print("Could not log in to PostgreSQL: " + error)
            password = None
            attempts += 1

    if conn is None:
        write_env_lines(lines)
        print("ERROR: PostgreSQL login failed 3 times. Check that PostgreSQL is running, then run install.bat again.")
        raise SystemExit(1)

    set_value(lines, "DB_HOST", host)
    set_value(lines, "DB_NAME", dbName)
    set_value(lines, "DB_USER", user)
    set_value(lines, "DB_PASSWORD", password)
    write_env_lines(lines)

    # step 4 - create the database if it isn't there
    conn.autocommit = True  # CREATE DATABASE can't run inside a transaction
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbName,))
    if cur.fetchone() is None:
        cur.execute('CREATE DATABASE "' + dbName.replace('"', '') + '"')
        print("Created database " + dbName)
    else:
        print("Database " + dbName + " already exists")
    cur.close()
    conn.close()

    print("")
    print("Admin login (also saved in .env): " + get_value(lines, "ADMIN_USERNAME") + " / " + adminPassword)


if __name__ == "__main__":
    main()
