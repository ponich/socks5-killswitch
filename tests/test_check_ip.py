from __future__ import annotations

import responses
from requests.exceptions import ConnectionError as ReqConnectionError

from socks5_killswitch import ProxyError, SafeSession

from .conftest import IP_CHECK_URL, PROXY_IP, PROXY_URL, REAL_IP


class TestCheckIp:
    @responses.activate
    def test_different_ip_ok(self, session: SafeSession) -> None:
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        result = session.check_ip()
        assert result == PROXY_IP
        assert session._killed is False

    @responses.activate
    def test_same_ip_leak(self, session: SafeSession) -> None:
        responses.get(IP_CHECK_URL, body=REAL_IP)
        try:
            session.check_ip()
        except ProxyError as e:
            assert "LEAK DETECTED" in str(e)
            assert session._killed is True
        else:
            raise AssertionError("ProxyError not raised")

    @responses.activate
    def test_network_failure(self, session: SafeSession) -> None:
        responses.get(IP_CHECK_URL, body=ReqConnectionError("timeout"))
        try:
            session.check_ip()
        except ProxyError as e:
            assert "IP check failed" in str(e)
            assert session._killed is True
        else:
            raise AssertionError("ProxyError not raised")

    @responses.activate
    def test_bypass_kill_switch(self, killed_session: SafeSession) -> None:
        """check_ip() must work even when kill switch is active."""
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        result = killed_session.check_ip()
        assert result == PROXY_IP

    @responses.activate
    def test_strips_whitespace(self, session: SafeSession) -> None:
        responses.get(IP_CHECK_URL, body=f"  {PROXY_IP}\n")
        result = session.check_ip()
        assert result == PROXY_IP

    @responses.activate
    def test_custom_ip_check_url(self) -> None:
        custom_url = "https://custom.ip.service/check"
        s = SafeSession(PROXY_URL, REAL_IP, ip_check_url=custom_url)
        responses.get(custom_url, body=PROXY_IP)
        result = s.check_ip()
        assert result == PROXY_IP
