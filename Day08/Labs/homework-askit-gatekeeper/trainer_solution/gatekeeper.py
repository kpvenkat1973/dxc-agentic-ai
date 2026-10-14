"""AskIT Gatekeeper v2 - trainer model solution. Built strictly from SPEC.md."""
import re

# ---------- R1 route ----------
_TEAMS = [  # order matters: first match wins
    ("Security", ("phishing", "malware", "breach", "suspicious", "ransomware")),
    ("Access", ("password", "locked", "login", "mfa", "access")),
    ("Network", ("vpn", "wifi", "network", "internet")),
    ("Hardware", ("laptop", "printer", "screen", "keyboard", "phone")),
]


def _has_word(text, word):
    """Whole-word, case-insensitive match."""
    return re.search(r"\b" + re.escape(word) + r"\b", text, re.IGNORECASE) is not None


def route(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string")
    for team, words in _TEAMS:
        if any(_has_word(text, w) for w in words):
            return team
    return "General"


# ---------- R2 needs_approval ----------
READ_ACTIONS = {"search_kb", "get_ticket"}
WRITE_ACTIONS = {"reset_password", "update_ticket", "grant_access"}
VIP_USERS = {"EMP-1001", "EMP-1012", "EMP-1023"}

D1_VIP_READ_NEEDS_APPROVAL = False   # D1: no
D2_NIGHT_APPROVER = "on-call"        # D2: on-call
D3_RETENTION_DAYS = 30               # D3: recorded for design, not enforced here


def _is_night(hour: int) -> bool:
    return hour >= 20 or hour < 8


def needs_approval(action: str, user_id: str, hour: int) -> dict:
    if action not in READ_ACTIONS and action not in WRITE_ACTIONS:
        raise ValueError(f"unknown action: {action!r}")
    if not isinstance(hour, int) or isinstance(hour, bool) or not 0 <= hour <= 23:
        raise ValueError("hour must be an int from 0 to 23")

    vip = user_id in VIP_USERS
    if action in READ_ACTIONS:
        if vip and D1_VIP_READ_NEEDS_APPROVAL:                       # rule 1
            return {"approval": True, "approver": "it manager"}
        return {"approval": False, "approver": "none"}               # rules 1/2
    if vip:                                                          # rule 3
        return {"approval": True, "approver": "it manager"}
    if _is_night(hour):                                              # rule 4
        return {"approval": True, "approver": D2_NIGHT_APPROVER}
    return {"approval": True, "approver": "service desk lead"}       # rule 5


# ---------- R3 safe_to_remember ----------
_BLOCKED_WORDS = ("password", "passcode", "otp", "pin", "address")  # 'address' added in v2


def safe_to_remember(text: str) -> bool:
    if not isinstance(text, str) or not text.strip():
        return False
    if any(_has_word(text, w) for w in _BLOCKED_WORDS):  # also covers "home address"
        return False
    if re.search(r"\d{6,}", re.sub(r"[\s-]", "", text)):
        return False
    return True
