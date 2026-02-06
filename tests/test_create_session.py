from __future__ import annotations

import logging

import responses
from requests.exceptions import ConnectionError as ReqConnectionError

from socks5_killswitch import ProxyError, SafeSession, create_session

from .conftest import IP_CHECK_URL, PROXY_IP, REAL_IP


class TestCreateSession:
    @responses.activate
    def test_returns_safe_session(self) -> None:
        responses.get(IP_CHECK_URL, body=REAL_IP)
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        s = create_session("host", 1080, "user", "pass", preflight=False)
        assert isinstance(s, SafeSession)

    @responses.activate
    def test_proxy_url_format(self) -> None:
        responses.get(IP_CHECK_URL, body=REAL_IP)
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        s = create_session("myhost", 9999, "myuser", "mypass", preflight=False)
        assert s._proxy_url == "socks5://myuser:mypass@myhost:9999"

    @responses.activate
    def test_detects_real_ip_then_proxy_ip(self) -> None:
        responses.get(IP_CHECK_URL, body=REAL_IP)
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        s = create_session("host", 1080, "user", "pass", preflight=False)
        assert s._real_ip == REAL_IP

    @responses.activate
    def test_proxy_unreachable(self) -> None:
        responses.get(IP_CHECK_URL, body=REAL_IP)
        responses.get(IP_CHECK_URL, body=ReqConnectionError("refused"))
        try:
            create_session("host", 1080, "user", "pass", preflight=False)
        except ProxyError as e:
            assert "IP check failed" in str(e)
        else:
            raise AssertionError("ProxyError not raised")

    @responses.activate
    def test_logs_instead_of_print(self, caplog: logging.LogCaptureFixture) -> None:
        responses.get(IP_CHECK_URL, body=REAL_IP)
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        with caplog.at_level(logging.INFO, logger="socks5_killswitch"):
            create_session("host", 1080, "user", "pass", preflight=False)
        assert "Proxy OK" in caplog.text
        assert PROXY_IP in caplog.text

    @responses.activate
    def test_custom_timeout(self) -> None:
        responses.get(IP_CHECK_URL, body=REAL_IP)
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        s = create_session("host", 1080, "user", "pass", timeout=60, preflight=False)
        assert s.timeout == 60

    @responses.activate
    def test_custom_ip_check_url(self) -> None:
        custom_url = "https://custom.service/ip"
        responses.get(custom_url, body=REAL_IP)
        responses.get(custom_url, body=PROXY_IP)
        s = create_session("host", 1080, "user", "pass", ip_check_url=custom_url, preflight=False)
        assert s._ip_check_url == custom_url

    @responses.activate
    def test_leak_on_create(self) -> None:
        """If proxy returns the real IP, create_session must fail."""
        responses.get(IP_CHECK_URL, body=REAL_IP)
        responses.get(IP_CHECK_URL, body=REAL_IP)
        try:
            create_session("host", 1080, "user", "pass", preflight=False)
        except ProxyError as e:
            assert "LEAK DETECTED" in str(e)
        else:
            raise AssertionError("ProxyError not raised")
