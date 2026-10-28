# Treasure Tokens — Payment Token System

Iteration 3 · Treasure Row

Treasure Tokens (TT) are Treasure Row's in-app currency for paying at checkout.
They let the app handle "funds" safely without touching real money: **no card
numbers, bank details, or payment processors are involved**, which keeps the
project consistent with the requirement that sensitive payment data is never
collected or stored. Items are still exchanged in person; tokens replace the
cash at that meetup.

**1 TT = $1.00 of listing price.**

---

## How it works

```
 Buyer wallet                 Escrow (per seller)                Seller wallet
 ┌────────────┐  checkout   ┌──────────────────────┐  pickup    ┌────────────┐
 │  200.00 TT │ ──────────▶ │ 40.00 TT  HELD        │ ─────────▶ │  +40.00 TT │
 └────────────┘  (debit)    │ code only buyer sees  │ (seller    └────────────┘
       ▲                    └──────────────────────┘  enters code)
       │        cancel before pickup (buyer / seller / admin)
       └──────────────────────── refund ◀───────────────────────────────
```

1. **Wallets are issued automatically.** The first time a user's wallet is
   needed (checkout, wallet page, header balance), it is opened with a
   starting balance — `TOKEN_STARTING_BALANCE`, default **200 TT** — recorded
   in the ledger as `STARTING_BALANCE`.
2. **Admins can grant tokens** from the admin dashboard (0.01–10,000 TT per
   grant, with an optional note). Recorded as `ADMIN_GRANT` with the admin's
   name.
3. **Checkout pays with tokens.** The cart is re-priced from the database, the
   buyer's balance is checked, and the order total is moved from the buyer's
   wallet into **escrow — one escrow per seller** in the order. Recorded as
   `ESCROW_HOLD`.
4. **Pickup codes.** Each escrow has a one-time pickup code (`XXXX-XXXX`) that
   only the buyer can see — on the order confirmation page and in
   *My Account → Wallet*.
5. **Release at the meetup.** The buyer hands the seller their code after
   receiving the items. The seller enters it in *My Account → Sales History*;
   the tokens move to the seller's wallet (`ESCROW_RELEASE`). When every
   seller in an order has been paid, the order becomes `COMPLETED`.
6. **Refunds.** Before pickup, the buyer, the seller, or an admin can cancel;
   the tokens go back to the buyer (`ESCROW_REFUND`) and the order becomes
   `CANCELLED` (or `PARTIALLY_COMPLETED` if some sellers were already paid).

---

## How tokens are validated (safety rules)

| Rule | How it's enforced |
|---|---|
| A balance can never go negative | `CHECK (balance >= 0)` on `wallets.balance`, plus a balance check before the order is created |
| No double-spending | Checkout locks the buyer's wallet row (`SELECT … FOR UPDATE`) while debiting it |
| Money moves are all-or-nothing | The debit, escrow rows, and ledger entries are written in one database transaction; if the hold fails, the unpaid order is deleted |
| Prices can't be faked | The cart is re-priced from the database at checkout (the browser's price is ignored) |
| Only the seller can release, only once | Server checks the signed-in user is the escrow's seller and that the escrow is still `HELD` |
| Codes can't be guessed | 8 random characters from a 29-character alphabet; **5 wrong codes lock the escrow** (`LOCKED`) until an admin reviews it |
| Codes aren't stored | Each escrow stores only a random nonce; the code is `HMAC-SHA256(SECRET_KEY, "<escrow id>:<nonce>")`, so a copy of the database alone reveals no codes. (Changing `SECRET_KEY` changes the codes of escrows still held.) |
| Codes are easy to read aloud | No look-alike characters: no `I/L/1`, `O/0`, `U/V` |
| Sellers never see the code | The API includes `pickup_code` only for the buyer |
| Every change is auditable | Every balance change writes a `token_ledger` row in the same transaction, so **balance = sum of ledger entries** for every wallet |

---

## Data model

| Table | Purpose |
|---|---|
| `wallets` | `user_id` (PK), `balance NUMERIC(12,2) CHECK (balance >= 0)` |
| `order_escrow` | One row per (order, seller): `amount`, `status` (`HELD`, `RELEASED`, `REFUNDED`, `LOCKED`), `code_nonce`, `failed_attempts` |
| `token_ledger` | Append-only history: `user_id`, signed `amount`, `entry_type`, optional `order_id` / `escrow_id`, `note`, `created_by` |

Created by `backend/init_db.py` (`CREATE TABLE IF NOT EXISTS`, so existing data is untouched).

## API

| Method | Path | Who | Purpose |
|---|---|---|---|
| GET | `/api/wallet` | signed-in user | balance, ledger, purchases (with pickup codes), sales awaiting pickup |
| POST | `/api/checkout/complete` | signed-in user | pays with tokens; response includes each seller's pickup code |
| POST | `/api/escrow/<id>/release` | seller | `{"code": "XXXX-XXXX"}` — confirm pickup |
| POST | `/api/escrow/<id>/cancel` | buyer / seller / admin | refund the buyer before pickup |
| GET | `/admin/wallets` | admin | every user's balance |
| POST | `/admin/wallets/<user_id>/grant` | admin | `{"amount": 50, "note": "..."}` |
| GET | `/admin/escrow` | admin | held and locked pickups |
| POST | `/admin/escrow/<id>/refund` | admin | refund a held or locked pickup |

Code: `backend/models/wallet_model.py` (SQL), `backend/services/wallet_service.py`
(rules), `backend/controllers/wallet_controller.py` (API), admin routes in
`backend/controllers/admin_controller.py`.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `TOKEN_STARTING_BALANCE` | `200` | Tokens every new wallet starts with |
| `SECRET_KEY` | (required) | Also the key for pickup codes |

## How it's tested

`backend/tests/test_wallet.py` (21 tests, run against the local test database —
see the app README) covers: starting balance; escrow per seller at checkout;
insufficient tokens (no order created, stock unchanged); a balance that drops
mid-checkout (unpaid order removed); release with the right code, wrong-code
lockout after 5 tries, release only by the seller and only once; codes not
stored in the database and never shown to sellers; refunds by buyer, seller,
and admin; admin grants and their limits; and the buyer seeing their codes on
the confirmation page. Every test also asserts **balance = sum of ledger**.

## Known limits

- Cancelling an order refunds the tokens but does not put the items back into
  stock (same as the existing order flow).
- Held escrows don't expire automatically; an admin can refund stale ones from
  the dashboard.
- Tokens have no cash value and can't be withdrawn.
