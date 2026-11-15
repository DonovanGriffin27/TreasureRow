# Treasure Row: Beta Release

Treasure Row is a campus marketplace for Hampton University students. Students open a storefront, list clothing, and buy from each other. Checkout uses **Treasure Tokens**, an in-app currency (1 TT = $1), so no real money or card numbers are involved.

This is the Beta Release for CSC 404. It runs on your own computer with a local database.

## Requirements

- **Python 3.12 or newer**
- **PostgreSQL**, running on your computer
  - Mac: [Postgres.app](https://postgresapp.com) (open it and click Start)
  - Windows: the installer from [postgresql.org](https://www.postgresql.org/download/windows/) (remember the password you set for the `postgres` user)
- An internet connection for the first install (to download the Python packages)
- No AWS account is needed. Without AWS keys, uploaded images are saved on your computer.

## Install and launch on a Mac (one click)

1. Unzip the Beta zip. You get a folder named `TreasureRow`.
2. Make sure Postgres.app is open and started.
3. Open the `TreasureRow` folder. Double-click **`install.sh`** if your Mac opens it in Terminal, otherwise open Terminal in the folder and run:
   ```
   bash install.sh
   ```
   It checks Python, creates a virtual environment, installs the requirements, creates your `.env` file with a new random secret key, creates the database, and creates the tables.
   **At the end it prints the admin username and password. Write them down.** They are shown only once (they are also in your `.env` file).
4. Double-click **`Launch TreasureRow.command`**. The app starts and your browser opens at <http://127.0.0.1:5001>. Press Control+C in the Terminal window to stop it.

If the Mac refuses to open the files, see Troubleshooting below.

## Install and launch on Windows (manual steps)

There is no one-click installer for Windows yet. In PowerShell, from inside the `TreasureRow` folder:

```
py -3.12 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Open `.env` in a text editor and set these values:

- `SECRET_KEY`: any long random text. You can make one with `python -c "import secrets; print(secrets.token_hex(32))"`
- `ADMIN_USERNAME` and `ADMIN_PASSWORD`: pick your own admin login
- `DB_USER=postgres` and `DB_PASSWORD`: the password you set when installing PostgreSQL
- `MAIL_SERVER`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`: leave all four blank

Then create the database and start the app:

```
createdb -U postgres treasurerow
python backend\init_db.py
flask --app app run --port 5001
```

If `createdb` is not found, open **pgAdmin** or **SQL Shell (psql)** and run `CREATE DATABASE treasurerow;`. After `init_db.py` you should see `DATABASE INITIALIZED`. Open <http://127.0.0.1:5001>.

## Test accounts

There are no built-in student accounts. Make your own so no password is shared in this package.

- **Student accounts:** click **Create Account**. Use any address ending in `@my.hamptonu.edu` (it does not need to be a real mailbox, for example `seller1@my.hamptonu.edu` and `buyer1@my.hamptonu.edu`). The username must be 3 to 50 characters and the password 8 to 128 characters. Make two accounts so you can test buying and selling.
- **Admin account:** go to <http://127.0.0.1:5001/auth/admin-login>. Mac: use the username and password the installer printed. Windows: use the `ADMIN_USERNAME` and `ADMIN_PASSWORD` you put in `.env`.

## Quick tour (about 5 minutes)

1. Sign in as `seller1`, create a storefront, and add a listing with a photo.
2. Sign out, sign in as `buyer1`, add the listing to the cart, and check out. A new wallet starts with **200 TT**.
3. After checkout the buyer sees a one-time pickup code (`XXXX-XXXX`) on the confirmation page and in My Account, Wallet.
4. Sign back in as `seller1` and enter that code under My Account, Sales History. The tokens move to the seller's wallet.
5. In the admin account you can grant extra tokens from the admin dashboard.

## Troubleshooting

| Problem | Fix |
|---|---|
| "Permission denied" or the Mac will not run the files | In Terminal, in the folder: `chmod +x install.sh "Launch TreasureRow.command"`, then try again. Or run `bash install.sh` and `bash "Launch TreasureRow.command"`. |
| Mac says the file is from an unidentified developer | Right-click the file, choose **Open**, then **Open** again. |
| `PostgreSQL is not reachable` | Open Postgres.app and click Start, then run the installer again. If your Postgres has a password, put it in `DB_PASSWORD` in `.env`. |
| `Python 3.12 or newer was not found` | Install Python from [python.org](https://www.python.org/downloads/) (or `brew install python@3.12`), then run the installer again. |
| Blank page on port 5000 | On a Mac, AirPlay Receiver uses port 5000. Treasure Row uses **5001**, so open `http://127.0.0.1:5001`. |
| `Port 5001 is already in use` | Another copy of Treasure Row is running. Stop it with Control+C, or restart your computer. |
| `SECRET_KEY` error when starting | `.env` is missing or still has `SECRET_KEY=change-me`. Delete `.env` and run the installer again (Mac), or set a real random key (Windows). |
| `We couldn't reach the database` | PostgreSQL is not running, or `DB_USER` / `DB_PASSWORD` in `.env` are wrong. |
| Signup says to use a student email | Only addresses ending in `@my.hamptonu.edu` are accepted. |
| Start over from scratch | Delete the `venv` folder and the `.env` file, then run the installer again. |

## Known issues

- There is no one-click installer for Windows yet. Use the manual steps above.
- The Mac installer was written for Postgres.app / Homebrew Postgres (your Mac username, no password). Other setups need `DB_USER` and `DB_PASSWORD` edited in `.env`.
- Password-reset emails are not sent in this package. The reset link is printed in the Terminal window instead (mail is switched off on purpose so no email password ships with the app).
- Uploaded images are stored on your computer, not in Amazon S3.
- There is no limit on how many times someone can try a wrong password at sign-in. This is planned for a later iteration.
- The package runs Flask's built-in server. It is meant for local testing, not for hosting on the internet. The live team deployment runs on AWS Elastic Beanstalk.
- Tokens have no real-world value and cannot be cashed out.

## Security notes

- This package contains no passwords, keys, or `.env` file. Your `.env` is created on your computer by the installer and is never part of the zip.
- Never commit or share your `.env` file.
