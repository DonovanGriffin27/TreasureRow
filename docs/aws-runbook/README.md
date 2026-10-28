# AWS Network Runbook — Treasure Row

**Owner:** Jonah Goodwine (backup: Noah Higgs)
**Last updated:** 10/27/26 — implements the "AWS Database Access Blocked" fix from the Risk Assessment

Use this when you need access to the team's AWS database, when the app can't reach it, when deploying, or before a demo.

---

## What's in AWS

| Resource | Name | Region |
|---|---|---|
| Database (RDS PostgreSQL) | `treasurerow-db` | us-east-2 (Ohio) |
| Database firewall (security group) | `treasurerow-db-sg` (`sg-0b41c026b3fd76924`) | us-east-2 |
| Image storage (S3) | `treasurerow-images-hu2026-...` bucket | us-east-2 |
| Hosting (Elastic Beanstalk) | App `treasurerow`, environment `treasurerow-env` — single instance, t3.micro, Python 3.14 on Amazon Linux 2023 | us-east-2 |
| Beanstalk server firewall | `sg-0d6504687307a917b` (name starts with `awseb-`) | us-east-2 |

**Live site:** http://treasurerow.us-east-2.elasticbeanstalk.com

Real hostnames, usernames, passwords and keys are **never** written here, in Jira, or in the group chat. Ask Jonah or Noah for them privately.

---

## Security group rules the app needs

All rules are on **`treasurerow-db-sg`**, **Inbound**.

| Type | Port | Source | Description | Who it's for |
|---|---|---|---|---|
| PostgreSQL | 5432 | `sg-0d6504687307a917b` (Beanstalk server) | `Elastic Beanstalk` | The deployed site |
| PostgreSQL | 5432 | One IP as `x.x.x.x/32` (pick **My IP**) | e.g. `Noah - home` | Local testing against AWS, one rule per person per network |

**Outbound:** leave the default (all traffic, `0.0.0.0/0`).

Rules:
- **Never** add `0.0.0.0/0` on port 5432 — that opens the database to the whole internet.
- **Never** edit or delete someone else's rule — use **Add rule** for yourself.
- Always fill in **Description** so stale rules are easy to find.
- If the Beanstalk environment is ever recreated, its security group ID changes — see Runbook 5.

---

## Runbook 1: Get access (first time)

1. **Accept the invite.** Open the AWS invite email for the **Treasure Row** project (check spam; it expires after 14 days) and create an AWS Builder ID.
2. **Sign in** at **settings.aws.com** → click **Treasure Row** to open the console. Region must be **us-east-2** (check the address bar).
3. **Make sure the database is running.** Search **RDS** → **Databases** → `treasurerow-db`. If the status is **Stopped**: check its box → **Actions → Start**, then wait for **Available** (5–10 minutes).
4. **Allow your IP.**
   1. On `treasurerow-db`, open **Connectivity & security** → under **Security group rules**, click **treasurerow-db-sg** (either row opens the same group).
   2. Check the box next to the group → **Actions → Edit inbound rules**.
   3. **Add rule** → Type **PostgreSQL** → Source **My IP** → Description: your name + network (e.g. `Jonah - campus`) → **Save rules**.
   4. Repeat whenever you change networks (home vs. campus). Everyone on campus Wi-Fi usually shares one IP — check "what is my ip" first; if it's already listed, skip this.
5. **Point your app at AWS.** In `app/.env`:
   - Put `#` in front of your four local lines: `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` (keep `DB_PORT=5432`).
   - Fill in the AWS values Jonah/Noah send you privately: `DB_HOST`, `DB_NAME=treasurerow`, `DB_USER`, `DB_PASSWORD`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET`, `AWS_REGION=us-east-2`, `DB_SSLMODE=require`.
   - `SECRET_KEY`, `ADMIN_USERNAME` and `ADMIN_PASSWORD` are **not** shared — make your own. Generate a key with `python3 -c "import secrets; print(secrets.token_hex(32))"` (Windows: `py`).
6. **Verify.** From `app/`, run `python3 app.py` (Windows: `py app.py`), open http://127.0.0.1:5001, and log in. Or check the tables directly:
   ```
   psql "host=<DB_HOST> port=5432 dbname=treasurerow user=<DB_USER> sslmode=require"
   \dt
   ```

---

## Runbook 2: "The app can't connect to the database"

Read the error first:

| Error | Cause | Fix |
|---|---|---|
| `timeout` / app hangs ~5 seconds | Your IP isn't allowed, or the DB is stopped | Runbook 1, steps 3–4 |
| `password authentication failed` | Wrong `DB_USER` / `DB_PASSWORD` | Re-copy the values sent privately; no spaces or quotes |
| `database "treasurerow" does not exist` | Wrong `DB_NAME` | `DB_NAME=treasurerow` |
| App won't start: `SECRET_KEY is not set` | Missing key | Add `SECRET_KEY` to `.env` (Runbook 1, step 5) |
| Images save to `/static/uploads/` instead of S3 | An `AWS_` value is missing or wrong | Re-check the four `AWS_` lines |

---

## Runbook 3: "The deployed site can't reach the database"

1. Make sure RDS `treasurerow-db` is **Available** (Runbook 1, step 3). The live site goes down whenever RDS is stopped.
2. Make sure **treasurerow-db-sg** has the `Elastic Beanstalk` rule with the **current** Beanstalk security group (Elastic Beanstalk → `treasurerow-env` → **Configuration → Instance traffic and scaling** → EC2 security groups, name starts with `awseb-`).
3. **Configuration → Environment properties** must include `SECRET_KEY`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_BUCKET` (Source: plain text). `DB_PORT`, `DB_SSLMODE` and `AWS_REGION` come from `app/.ebextensions/env.config`.
4. **Actions → Restart app server(s)**, then check **Logs → Request logs → Last 100 lines** for `Connection Error`.

---

## Runbook 4: Deploy new code to the live site

1. Commit your changes on your branch (only committed files are deployed).
2. From the repo root, build the bundle:
   ```
   git archive -o treasurerow-eb.zip HEAD:app
   ```
   (This leaves out `.env` and `venv` automatically.)
3. Elastic Beanstalk → `treasurerow-env` → **Upload and deploy** → choose the zip → version label (e.g. `v2-messaging-fix`) → **Deploy**.
4. Wait for health **Ok**, then test the live site.

---

## Runbook 5: Shut down and bring back (save credits)

Single-instance environments **can't be paused** — the server runs (and uses credits) until terminated.

**Shut down** (after grading/demos):
1. Elastic Beanstalk → `treasurerow-env` → **Actions → Save configuration** → name it (e.g. `treasurerow-iteration3`). This keeps every setting and environment property.
2. **Actions → Terminate environment**.
3. RDS → `treasurerow-db` → **Actions → Stop temporarily** (AWS restarts it automatically after 7 days).

**Bring back:**
1. Start RDS and wait for **Available**.
2. Elastic Beanstalk → **Applications → treasurerow → Saved configurations** → select it → **Launch environment**.
3. **The new environment has a new security group.** Add its `sg-...` to `treasurerow-db-sg` (Type PostgreSQL, Description `Elastic Beanstalk`) and delete the old Beanstalk rule. Update the IDs in this file.
4. If the `treasurerow` domain was taken meanwhile, the site link changes — update it here.

---

## Before a demo (checklist)

- [ ] RDS status is **Available** (start it ~10 minutes early)
- [ ] Elastic Beanstalk health is **Ok** and the live site loads
- [ ] Your current IP is in the inbound rules (only needed for local testing against AWS)

## After testing

- Never stop RDS while the live site needs to work.
- When the site isn't needed, follow Runbook 5.
- Delete inbound rules for people or networks that no longer need access.