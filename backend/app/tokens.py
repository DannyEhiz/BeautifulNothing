from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from . import config

_admin = URLSafeTimedSerializer(config.SECRET_KEY, salt="bn-admin-session")
_email_action = URLSafeTimedSerializer(config.SECRET_KEY, salt="bn-email-action")

ADMIN_SESSION_MAX_AGE = 7 * 24 * 3600
EMAIL_ACTION_MAX_AGE = 30 * 24 * 3600


def make_admin_token() -> str:
    return _admin.dumps({"role": "admin"})


def check_admin_token(token: str) -> bool:
    try:
        return _admin.loads(token, max_age=ADMIN_SESSION_MAX_AGE).get("role") == "admin"
    except (BadSignature, SignatureExpired):
        return False


def make_action_token(order_id: str, action: str) -> str:
    return _email_action.dumps({"order": order_id, "action": action})


def read_action_token(token: str) -> dict | None:
    try:
        return _email_action.loads(token, max_age=EMAIL_ACTION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
