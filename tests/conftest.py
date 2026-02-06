from __future__ import annotations

import pytest
import responses

from socks5_killswitch import SafeSession

PROXY_URL = "socks5://testuser:testpass@proxy.example.com:1080"
REAL_IP = "1.2.3.4"
PROXY_IP = "5.6.7.8"
IP_CHECK_URL = "https://api.ipify.org"
TEST_URL = "https://httpbin.org/get"


@pytest.fixture()
def session() -> SafeSession:
    """A fresh SafeSession with mocked IPs (preflight off for unit tests)."""
    return SafeSession(PROXY_URL, REAL_IP, preflight=False)


@pytest.fixture()
def killed_session() -> SafeSession:
    """A SafeSession with the kill switch already active."""
    s = SafeSession(PROXY_URL, REAL_IP, preflight=False)
    s._killed = True
    return s


@pytest.fixture()
def mocked_responses():
    """Activate the responses mock for the duration of a test."""
    with responses.RequestsMock() as rsps:
        yield rsps
