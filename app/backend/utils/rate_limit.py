# -*- coding: utf-8 -*-
#Rate limiting & Login Lockout SCRUM-114
import time

reset_requests = {} #list of times a reset is requested
login_attempts = {}  #number of failed attempts
lockout_time = {} #lockout timer

def reset_request(email):
    now = time.time()
    email = email.strip().lower()
    recent = [t for t in reset_requests.get(email, []) if now - t < 900]
    if len(recent) >= 3:
        reset_requests[email] = recent
        return False
    recent.append(now)
    reset_requests[email] = recent
    return True

def login_locked_timer(username):
    now = time.time()
    username = (username or "").strip().lower()  # a form posted with no username must not crash
    until = lockout_time.get(username)
    if until is None:
        return 0
    if now >= until:
      lockout_time.pop(username)
      login_attempts.pop(username, None)
      return 0
    return int(until - now) + 1

def record_login_fails(username):
    username = (username or "").strip().lower()  # a form posted with no username must not crash
    login_attempts[username] = login_attempts.get(username, 0) + 1
    if login_attempts[username] >= 5:
        lockout_time[username] = time.time() + 900
        login_attempts.pop(username, None)
        return True
    return False

def record_login_success(username):
    username = (username or "").strip().lower()  # a form posted with no username must not crash
    login_attempts.pop(username, None)
    lockout_time.pop(username, None)

def reset_all():
    reset_requests.clear()
    login_attempts.clear()
    lockout_time.clear()