"""Client acceptance tests for the AskIT Gatekeeper homework. Kept OUTSIDE the homework folder on purpose."""
import importlib
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
gk = importlib.import_module("gatekeeper")


# ---------------- R1 route ----------------
@pytest.mark.parametrize("text,team", [
    ("VPN error 809 since morning", "Network"),                       # AC1
    ("Locked out after password change", "Access"),                    # AC2
    ("My laptop screen is flickering", "Hardware"),                    # AC3
    ("Got a suspicious email with a strange link", "Security"),       # AC4
    ("Please install Python for me", "General"),                       # AC5
    ("Phishing email asked for my password", "Security"),             # AC6 order: Security first
    ("Cannot download files", "General"),                              # AC7 whole words: 'download' is not 'down'
])
def test_route(text, team):
    assert gk.route(text) == team


def test_route_empty():                                                # AC8
    with pytest.raises(ValueError):
        gk.route("")


# ---------------- R2 needs_approval ----------------
def test_read_needs_no_approval():                                     # AC9
    r = gk.needs_approval("search_kb", "EMP-1002", 10)
    assert r["approval"] is False


def test_write_needs_approval_daytime():                               # AC10
    r = gk.needs_approval("reset_password", "EMP-1002", 10)
    assert r["approval"] is True and r["approver"] == "service desk lead"


def test_write_at_night():                                             # AC11 (team decision D2: on-call OR queue)
    r = gk.needs_approval("reset_password", "EMP-1002", 23)
    assert r["approval"] is True and r["approver"] in ("on-call", "queue")


def test_vip_write():                                                  # AC12
    r = gk.needs_approval("update_ticket", "EMP-1001", 10)
    assert r["approval"] is True and r["approver"] == "it manager"


def test_vip_read_decision():                                          # AC13 (team decision D1: either is accepted)
    r = gk.needs_approval("get_ticket", "EMP-1012", 10)
    assert r["approval"] in (True, False)


def test_unknown_action():                                             # AC14
    with pytest.raises(ValueError):
        gk.needs_approval("delete_user", "EMP-1002", 10)


def test_bad_hour():                                                   # AC15
    with pytest.raises(ValueError):
        gk.needs_approval("search_kb", "EMP-1002", 24)


# ---------------- R3 safe_to_remember ----------------
@pytest.mark.parametrize("text,ok", [
    ("My laptop is a Dell XPS 13", True),                              # AC16
    ("I work from the Bengaluru office", True),                        # AC17
    ("My password is Summer2026", False),                              # AC18
    ("OTP 482913 for login", False),                                   # AC19
    ("Card 4111 1111 1111 1111 please", False),                        # AC20 long number with spaces
    ("", False),                                                       # AC21
])
def test_safe_to_remember(text, ok):
    assert gk.safe_to_remember(text) is ok


# ---------------- v2 client change + edge cases (trainer extras) ----------------
def test_v2_ransomware():
    assert gk.route("ransomware on my laptop") == "Security"


def test_v2_home_address():
    assert gk.safe_to_remember("My home address is 12 MG Road") is False


def test_vip_read_d1_no():
    assert gk.needs_approval("get_ticket", "EMP-1012", 10) == {"approval": False, "approver": "none"}


def test_night_boundaries():
    assert gk.needs_approval("grant_access", "EMP-1002", 20)["approver"] == "on-call"
    assert gk.needs_approval("grant_access", "EMP-1002", 7)["approver"] == "on-call"
    assert gk.needs_approval("grant_access", "EMP-1002", 8)["approver"] == "service desk lead"
    assert gk.needs_approval("grant_access", "EMP-1002", 19)["approver"] == "service desk lead"


def test_vip_write_at_night():
    assert gk.needs_approval("reset_password", "EMP-1023", 2)["approver"] == "it manager"


@pytest.mark.parametrize("h", [-1, 24, "10", 10.0, True])
def test_bad_hours(h):
    with pytest.raises(ValueError):
        gk.needs_approval("search_kb", "EMP-1002", h)


def test_blank_route():
    with pytest.raises(ValueError):
        gk.route("   ")


def test_pin_whole_word_only():
    assert gk.safe_to_remember("I like pinning notes") is True
    assert gk.safe_to_remember("My PIN is 1234") is False


def test_dashed_number():
    assert gk.safe_to_remember("Acct 123-456-789") is False
