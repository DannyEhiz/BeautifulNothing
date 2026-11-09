from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app import config


def _signer(salt: str) -> URLSafeTimedSerializer:
    # Built when used, not at import (the key may come from Cloudflare's env, or be generated).
    return URLSafeTimedSerializer(config.secret_key(), salt=salt)


ADMIN_SESSION_MAX_AGE = 7 * 24 * 3600
EMAIL_ACTION_MAX_AGE = 30 * 24 * 3600


def make_admin_token() -> str:
    return _signer("bn-admin-session").dumps({"role": "admin"})


def check_admin_token(token: str) -> bool:
    try:
        return _signer("bn-admin-session").loads(token, max_age=ADMIN_SESSION_MAX_AGE).get("role") == "admin"
    except (BadSignature, SignatureExpired):
        return False


def make_action_token(order_id: str, action: str) -> str:
    return _signer("bn-email-action").dumps({"order": order_id, "action": action})


def read_action_token(token: str) -> dict | None:
    try:
        return _signer("bn-email-action").loads(token, max_age=EMAIL_ACTION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
