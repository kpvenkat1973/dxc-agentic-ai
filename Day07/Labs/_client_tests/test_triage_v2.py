import pytest
from triage import triage

def t(title, users=1, desc="", tier=None):
    d = {"title": title, "description": desc, "affected_users": users}
    if tier:
        d["customer_tier"] = tier
    return d

# (ticket, expected priority, expected queue, expected sla_hours)
CASES = [
    (t("Printer jam", 60),                  "P1", "General",  2),
    (t("Email outage"),                     "P1", "General",  2),
    (t("VPN is DOWN", 1),                   "P1", "Network",  2),
    (t("Slow download speed"),              "P4", "General", 72),
    (t("Wifi dropping", 12),                "P2", "Network",  8),
    (t("URGENT: cannot print"),             "P2", "General",  8),
    (t("Keyboard broken", 3),               "P3", "Hardware", 24),
    (t("Need a mouse"),                     "P4", "General", 72),
    (t("Password reset"),                   "P4", "Access",  72),
    (t("Laptop wifi broken"),               "P4", "Network", 72),
    (t("Screen flicker", 2, "after login"), "P3", "Access",  24),
    (t("Account locked", 50),               "P1", "Access",   2),
    (t("Unlocked door", 1),                 "P4", "General", 72),
    # --- new in v2 ---
    (t("Need a mouse", tier="vip"),         "P3", "General", 24),
    (t("Keyboard broken", 3, tier="vip"),   "P2", "Hardware",  8),
    (t("Email outage", tier="vip"),         "P1", "General",  2),
    (t("Need a mouse", tier="standard"),    "P4", "General", 72),
    (t("Phishing email received"),          "P4", "Security", 72),
    (t("Malware on laptop wifi", 12),       "P2", "Security",  8),
    (t("Data breach suspected", 60),        "P1", "Security",  2),
]

@pytest.mark.parametrize("ticket,prio,queue,sla", CASES)
def test_rules(ticket, prio, queue, sla):
    assert triage(ticket) == {"priority": prio, "queue": queue, "sla_hours": sla}

def test_missing_users_defaults_to_one():
    assert triage({"title": "Need a mouse"})["priority"] == "P4"

def test_empty_title_rejected():
    with pytest.raises(ValueError):
        triage({"title": "  ", "affected_users": 1})

def test_bad_users_rejected():
    with pytest.raises(ValueError):
        triage(t("Need a mouse", 0))

def test_bad_tier_rejected():
    with pytest.raises(ValueError):
        triage(t("Need a mouse", tier="gold"))
