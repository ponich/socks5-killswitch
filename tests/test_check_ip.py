from __future__ import annotations

from unittest.mock import patch

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
        s = SafeSession(PROXY_URL, REAL_IP, ip_check_url=custom_url, preflight=False)
        responses.get(custom_url, body=PROXY_IP)
        result = s.check_ip()
        assert result == PROXY_IP


class TestPreflight:
    def test_preflight_fails_kills_switch(self) -> None:
        """Unreachable proxy triggers kill switch, no ipify request made."""
        s = SafeSession(PROXY_URL, REAL_IP, preflight=True)
        side_effect = OSError("Connection refused")
        with patch("socks5_killswitch.socket.create_connection", side_effect=side_effect):
            try:
                s.check_ip()
            except ProxyError as e:
                assert "Proxy unreachable" in str(e)
                assert s._killed is True
            else:
                raise AssertionError("ProxyError not raised")

    @responses.activate
    def test_preflight_disabled_skips_tcp_check(self) -> None:
        """With preflight=False, no TCP check happens."""
        s = SafeSession(PROXY_URL, REAL_IP, preflight=False)
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        with patch("socks5_killswitch.socket.create_connection") as mock_conn:
            result = s.check_ip()
            mock_conn.assert_not_called()
        assert result == PROXY_IP

    @responses.activate
    def test_preflight_succeeds_then_checks_ip(self) -> None:
        """Preflight passes → proceeds to ipify check as normal."""
        s = SafeSession(PROXY_URL, REAL_IP, preflight=True)
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        with patch("socks5_killswitch.socket.create_connection") as mock_conn:
            mock_sock = mock_conn.return_value
            result = s.check_ip()
            mock_conn.assert_called_once_with(("proxy.example.com", 1080), timeout=5)
            mock_sock.close.assert_called_once()
        assert result == PROXY_IP
