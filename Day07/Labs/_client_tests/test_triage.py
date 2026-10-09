import pytest
from triage import triage

def t(title, users=1, desc=""):
    return {"title": title, "description": desc, "affected_users": users}

# (ticket, expected priority, expected queue, expected sla_hours)
CASES = [
    (t("Printer jam", 60),                  "P1", "General",  4),
    (t("Email outage"),                     "P1", "General",  4),
    (t("VPN is DOWN", 1),                   "P1", "Network",  4),
    (t("Slow download speed"),              "P4", "General", 72),
    (t("Wifi dropping", 12),                "P2", "Network",  8),
    (t("URGENT: cannot print"),             "P2", "General",  8),
    (t("Keyboard broken", 3),               "P3", "Hardware", 24),
    (t("Need a mouse"),                     "P4", "General", 72),
    (t("Password reset"),                   "P4", "Access",  72),
    (t("Laptop wifi broken"),               "P4", "Network", 72),
    (t("Screen flicker", 2, "after login"), "P3", "Access",  24),
    (t("Account locked", 50),               "P1", "Access",   4),
    (t("Unlocked door", 1),                 "P4", "General", 72),
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
