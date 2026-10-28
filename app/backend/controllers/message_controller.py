"""
Author: Jonah Goodwine
Created: 10/15/26
CSC404
message_controller.py -- routes for buyer/seller messaging

  GET  /messages                      messages page
  GET  /api/messages                  list of my conversations
  GET  /api/messages/<other_id>       one conversation (?listing=<id> optional)
  POST /api/messages                  send {"receiver_id", "listing_id", "body"}
"""

from flask import Blueprint, jsonify, request, render_template

from models import message_model
from utils.auth_utils import get_session_user

message_bp = Blueprint("messages", __name__)

MAX_LENGTH = 1000 # longest message allowed


# returns my user id, or None (not signed in / .env admin has no id)
def get_my_id():
    user = get_session_user()
    if user is None:
        return None
    return user["id"]


# messages page
@message_bp.route("/messages")
def messages_page():
    return render_template("messages.html")


# list of conversations, newest first
@message_bp.route("/api/messages", methods=["GET"])
def list_conversations():
    myId = get_my_id()
    if myId is None:
        return jsonify({"error": "Sign in with a user account to use messages."}), 403

    rows = message_model.get_all_for_user(myId)
    conversations = []

    # rows are newest first, so the first row seen for a conversation is its latest message
    for row in rows:
        senderId = row[0]
        receiverId = row[1]
        listingId = row[2]

        # the other person is whoever isn't me
        if senderId == myId:
            otherId = receiverId
            otherName = row[7]
        else:
            otherId = senderId
            otherName = row[6]

        # look for this conversation in the list already
        found = False
        for convo in conversations:
            if convo["other_id"] == otherId and convo["listing_id"] == listingId:
                found = True
                break

        if not found:
            convo = {
                "other_id": otherId,
                "other_name": otherName,
                "listing_id": listingId,
                "listing_title": row[8],
                "last_message": row[3],
                "last_time": row[4].isoformat(),
                "unread": 0
            }
            conversations.append(convo)

        # count messages sent to me that I haven't read
        if receiverId == myId and not row[5]:
            convo["unread"] = convo["unread"] + 1

    return jsonify(conversations), 200


# one conversation, also marks it read
@message_bp.route("/api/messages/<int:other_id>", methods=["GET"])
def get_conversation(other_id):
    myId = get_my_id()
    if myId is None:
        return jsonify({"error": "Sign in with a user account to use messages."}), 403

    otherName = message_model.get_username(other_id)
    if otherName is None:
        return jsonify({"error": "User not found."}), 404

    listingId = request.args.get("listing", type=int)
    listingTitle = None
    if listingId is not None:
        listingTitle = message_model.get_listing_title(listingId)

    rows = message_model.get_thread(myId, other_id, listingId)
    message_model.mark_read(myId, other_id, listingId)

    messages = []
    for row in rows:
        messages.append({
            "id": row[0],
            "sender_id": row[1],
            "sender_name": row[2],
            "body": row[3],
            "created_at": row[4].isoformat(),
            "mine": row[1] == myId
        })

    return jsonify({
        "other_id": other_id,
        "other_name": otherName,
        "listing_id": listingId,
        "listing_title": listingTitle,
        "messages": messages
    }), 200


# send a message
@message_bp.route("/api/messages", methods=["POST"])
def send_message():
    myId = get_my_id()
    if myId is None:
        return jsonify({"error": "Sign in with a user account to use messages."}), 403

    data = request.get_json(silent=True) or {}
    body = (data.get("body") or "").strip()

    # check the receiver and listing ids are numbers
    try:
        receiverId = int(data.get("receiver_id"))
        listingId = data.get("listing_id")
        if listingId is not None and listingId != "":
            listingId = int(listingId)
        else:
            listingId = None
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid receiver or listing."}), 400

    # input checks
    if body == "":
        return jsonify({"error": "Message can't be empty."}), 400
    if len(body) > MAX_LENGTH:
        return jsonify({"error": "Message is too long (1000 characters max)."}), 400
    if receiverId == myId:
        return jsonify({"error": "You can't message yourself."}), 400
    if message_model.get_username(receiverId) is None:
        return jsonify({"error": "User not found."}), 404
    if listingId is not None and message_model.get_listing_title(listingId) is None:
        return jsonify({"error": "Listing not found."}), 404

    newId = message_model.send_message(myId, receiverId, listingId, body)
    return jsonify({"id": newId}), 201