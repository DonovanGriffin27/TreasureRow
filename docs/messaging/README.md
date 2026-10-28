# Messaging Feature — Treasure Row (Jonah Goodwine)

**Owner:** Jonah Goodwine · **Added:** Iteration 3 (October 2026) · **Branch:** jonah

## 1.0 Overview
Signed-in buyers and sellers can send each other text messages about a specific listing, so a buyer can ask about size, condition, or pickup before buying. Each conversation is between two users about one listing, and the Messages page shows how many unread messages are in each conversation.

## 2.0 How it works (user flow)
1. A signed-in buyer opens a storefront and clicks **Message Seller** on a listing card. The link only shows to signed-in users who don't own that storefront.
2. The link opens the Messages page (`/messages?to=<seller id>&listing=<listing id>`) with that conversation already open. The page is also in the nav menu.
3. The user types a message (up to 1000 characters) and clicks **Send**. Errors show under the message box.
4. The conversation list shows each conversation's other user, "Re: <listing title>", the latest message, and a red badge with the number of unread messages.
5. Opening a conversation marks the messages sent to you as read and clears the badge.
6. The page checks for new messages **every 10 seconds**, so replies show up without reloading. This is not real time; a reply can take up to 10 seconds to appear. While a conversation is open it reloads that conversation; otherwise it reloads the conversation list.

## 3.0 Files
| File | What it does |
|---|---|
| `app/backend/models/message_model.py` | All messaging SQL (send, load conversations, load one thread, mark read, look up usernames and listing titles) |
| `app/backend/controllers/message_controller.py` | The four messaging routes and all input checks |
| `app/templates/messages.html` | The Messages page: conversation list, open thread, send box, 10-second refresh |
| `app/app.py` | Registers `message_bp` |
| `app/templates/partials/_app_header.html` | Messages link in the nav menu |
| `app/static/js/storefront_view.js` | Message Seller link on each listing card |

## 4.0 Database
Uses the `messages` table (created in `init_db.py`). A conversation is every message between the same two users about the same listing, so there is no separate conversations table.

| Column | Type | Notes |
|---|---|---|
| `id` | SERIAL | Primary key |
| `sender_id` | INTEGER, NOT NULL | References `users(id)` ON DELETE CASCADE |
| `receiver_id` | INTEGER, NOT NULL | References `users(id)` ON DELETE CASCADE; CHECK `sender_id <> receiver_id` |
| `listing_id` | INTEGER, nullable | References `listings(id)` ON DELETE SET NULL |
| `body` | TEXT, NOT NULL | The message text (the 1000-character limit is checked in the controller, not the database) |
| `is_read` | BOOLEAN | Default false |
| `created_at` | TIMESTAMP | Default current time |

**What happens when data is deleted:**
- **A listing is deleted:** the conversation is kept. `listing_id` becomes empty, so the conversation just loses its "Re:" title.
- **A user is deleted:** every message they sent or received is deleted with them.
- **Messages with no listing:** the model compares listings with `IS NOT DISTINCT FROM`, because `NULL = NULL` isn't true in SQL. Without it, those conversations would never load.

## 5.0 Routes
| Method | Route | What it does | Success | Errors |
|---|---|---|---|---|
| GET | `/messages` | Messages page | 200 | Redirects to Sign In if signed out |
| GET | `/api/messages` | My conversations, newest first, with unread counts | 200 | 401, 403 |
| GET | `/api/messages/<other_id>?listing=<id>` | One conversation, oldest first; marks it read | 200 | 401, 403, 404 "User not found." |
| POST | `/api/messages` | Send `{"receiver_id", "listing_id", "body"}` | 201 + new id | 401, 403, 400, 404 (see 6.0) |

## 6.0 Rules (checked on the server)
| Rule | Error message | Status |
|---|---|---|
| You have to be signed in | Blocked by the sign-in check in `app.py` before the route runs (API calls get 401; the page redirects to Sign In) | 401 |
| You have to be a user account (the `.env` admin has no user id) | "Sign in with a user account to use messages." | 403 |
| You can't send empty messages (spaces are trimmed first, so "   " counts as empty) | "Message can't be empty." | 400 |
| Messages have a max length of 1000 characters (also enforced by the text box) | "Message is too long (1000 characters max)." | 400 |
| You can't message yourself (also blocked by a database CHECK) | "You can't message yourself." | 400 |
| The receiver has to exist | "User not found." | 404 |
| The listing has to exist (if one is given) | "Listing not found." | 404 |
| The ids have to be numbers | "Invalid receiver or listing." | 400 |

## 7.0 Security
- **The sender always comes from the login session**, never from the request, so nobody can send a message as someone else.
- All SQL uses parameters (`%s`), so message text can't change a query.
- Message text is escaped with `escapeHtml` before it's shown, so typed HTML or scripts appear as plain text.
- A user can only load conversations they're part of: every query filters on the signed-in user's id.

## 8.0 Testing
These match TC-42 to TC-48 in the Test Plan.

| Test | Expected |
|---|---|
| Message Seller on someone else's listing, send "hi" | Conversation opens tied to that listing; 201; message shows for both users |
| Send empty, 1001 characters, to yourself, to a missing user/listing | 400/404 with the matching error; nothing saved |
| POST with an extra `sender_id` for another user | Saved with the signed-in user as sender |
| A sends B two messages; B opens Messages, then the conversation | Badge shows 2, then clears |
| A and B both have the conversation open; A sends | B sees it within 10 seconds |
| Signed out; as `.env` admin; send `<script>alert(1)</script>` | 401; 403; shown as plain text |
| Open your own storefront | No Message Seller link |

## 9.0 Troubleshooting
| Problem | Likely cause |
|---|---|
| No Message Seller link | You're signed out, it's your own storefront, or the storefront didn't load its owner |
| "Sign in with a user account to use messages." | You're signed in as the `.env` admin; use a regular account |
| "Could not load messages." | The server or database is down; check the app logs and that RDS is running (see the AWS runbook) |
| A reply takes a few seconds to show up | Expected: the page checks every 10 seconds, not instantly |

## 10.0 Limitations and future work
- Messages are saved in the database so they don't go away when you log out or refresh.
- **Admins can't use messaging.** The admin login from `.env` has no user id, so the messaging routes return 403.
- No email or push notifications yet; you only see new messages on the Messages page.
- Messages can't be edited or deleted.
- **Polling cost:** each open Messages page sends one request every 10 seconds, and the conversation list is rebuilt from all of a user's messages each time. That's fine at class scale; with many users we'd add pagination, indexes on `sender_id` and `receiver_id`, or switch to WebSockets.
- **No rate limit:** a user could send many messages quickly. A per-user limit would be a good next step.

## Related documentation
- Requirements 3.1.6 (messages table) and 4.1.11 (Messaging function)
- Functional Specification 3.1.1.11 (Message object) and 4.1 (Messaging walkthrough)
- Design Specification 3.4.3.7 to 3.4.3.10 (messaging endpoints) and 3.6.3.8 (message model)
- Test Plan TC-42 to TC-48
