"""
wallet_controller.py

Treasure Row Campus Marketplace
Created by Donovan Griffin - Iteration 3

Treasure Tokens API (all routes need a signed-in user):

  GET  /api/wallet                     balance, ledger, purchases (with pickup
                                       codes) and sales awaiting pickup
  POST /api/escrow/<id>/release        seller confirms pickup with {"code": "..."}
  POST /api/escrow/<id>/cancel         buyer / seller / admin cancels before pickup
"""

from flask import Blueprint, jsonify, request

from services import wallet_service
from services.wallet_service import TokenError
from utils.auth_utils import get_session_user

wallet_bp = Blueprint("wallet", __name__, url_prefix="/api")


def _signed_in():
    user = get_session_user()
    if user is None:
        raise TokenError("Please sign in.", 401)
    from flask import session
    user["username"] = session.get("user")
    return user


@wallet_bp.errorhandler(TokenError)
def _token_error(e):
    return jsonify({"error": str(e)}), e.status


@wallet_bp.get("/wallet")
def get_wallet():
    user = _signed_in()
    if user["id"] is None:  # the .env admin account has no wallet
        raise TokenError("Admin accounts don't have a wallet.", 404)
    return jsonify(wallet_service.wallet_summary(user["id"])), 200


@wallet_bp.post("/escrow/<int:escrow_id>/release")
def release(escrow_id):
    user = _signed_in()
    data = request.get_json(silent=True) or {}
    return jsonify(wallet_service.release_escrow(user, escrow_id, data.get("code"))), 200


@wallet_bp.post("/escrow/<int:escrow_id>/cancel")
def cancel(escrow_id):
    user = _signed_in()
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip()[:200] or None
    return jsonify(wallet_service.cancel_escrow(user, escrow_id, reason)), 200
