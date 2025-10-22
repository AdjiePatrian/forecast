# auth/utils.py
"""
Utility helpers for auth subsystem.
- add password policy checks, random password generator, etc.
"""

import re
from werkzeug.security import generate_password_hash

def hash_password(password: str) -> str:
    return generate_password_hash(password)

def is_password_strong(password: str) -> bool:
    # example rule: min 8 chars, at least one digit and one letter
    if not password or len(password) < 8:
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[A-Za-z]", password):
        return False
    return True
