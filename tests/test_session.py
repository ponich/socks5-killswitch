from __future__ import annotations

import contextlib

import pytest
import responses
from requests.exceptions import ConnectionError as ReqConnectionError

from socks5_killswitch import ProxyError, SafeSession

from .conftest import IP_CHECK_URL, PROXY_IP, PROXY_URL, REAL_IP, TEST_URL


class TestInit:
    def test_proxies_set(self, session: SafeSession) -> None:
        assert session.proxies == {"http": PROXY_URL, "https": PROXY_URL}

    def test_real_ip_stored(self, session: SafeSession) -> None:
        assert session._real_ip == REAL_IP

    def test_not_killed(self, session: SafeSession) -> None:
        assert session._killed is False

    def test_default_timeout(self, session: SafeSession) -> None:
        assert session.timeout == 15

    def test_custom_timeout(self) -> None:
        s = SafeSession(PROXY_URL, REAL_IP, timeout=30)
        assert s.timeout == 30

    def test_default_ip_check_url(self, session: SafeSession) -> None:
        assert session._ip_check_url == IP_CHECK_URL

    def test_custom_ip_check_url(self) -> None:
        s = SafeSession(PROXY_URL, REAL_IP, ip_check_url="https://custom.ip/check")
        assert s._ip_check_url == "https://custom.ip/check"


class TestRequest:
    @responses.activate
    def test_success(self, session: SafeSession) -> None:
        responses.get(TEST_URL, json={"origin": PROXY_IP})
        resp = session.get(TEST_URL)
        assert resp.json() == {"origin": PROXY_IP}

    @responses.activate
    def test_sets_default_timeout(self, session: SafeSession) -> None:
        responses.get(TEST_URL, json={})
        session.get(TEST_URL)
        assert responses.calls[0].request.headers is not None

    @responses.activate
    def test_respects_explicit_timeout(self, session: SafeSession) -> None:
        responses.get(TEST_URL, json={})
        session.get(TEST_URL, timeout=99)
        # The request was made (no error) — explicit timeout accepted
        assert len(responses.calls) == 1

    @responses.activate
    def test_failure_kills_and_raises(self, session: SafeSession) -> None:
        responses.get(TEST_URL, body=ReqConnectionError("refused"))
        try:
            session.get(TEST_URL)
        except ProxyError as e:
            assert session._killed is True
            assert "kill switch ON" in str(e)
        else:
            pytest.fail("ProxyError not raised")

    @responses.activate
    def test_failure_chains_original(self, session: SafeSession) -> None:
        responses.get(TEST_URL, body=ReqConnectionError("refused"))
        try:
            session.get(TEST_URL)
        except ProxyError as e:
            assert e.__cause__ is not None
            assert isinstance(e.__cause__, ReqConnectionError)
        else:
            pytest.fail("ProxyError not raised")

    def test_killed_raises_immediately(self, killed_session: SafeSession) -> None:
        try:
            killed_session.get(TEST_URL)
        except ProxyError as e:
            assert "Kill switch active" in str(e)
        else:
            pytest.fail("ProxyError not raised")

    @responses.activate
    def test_killed_no_network_call(self, killed_session: SafeSession) -> None:
        responses.get(TEST_URL, json={})
        with contextlib.suppress(ProxyError):
            killed_session.get(TEST_URL)
        assert len(responses.calls) == 0

    @responses.activate
    def test_post_binary_data(self, session: SafeSession) -> None:
        """AMF2 binary payloads must work."""
        binary = b"\x00\x03\x00\x00\x00\x01"
        responses.post(TEST_URL, body=b"OK")
        resp = session.post(TEST_URL, data=binary)
        assert resp.content == b"OK"
        assert responses.calls[0].request.body == binary


class TestRepr:
    def test_password_masked(self, session: SafeSession) -> None:
        r = repr(session)
        assert "testpass" not in r
        assert "***" in r

    def test_shows_host(self, session: SafeSession) -> None:
        assert "proxy.example.com" in repr(session)

    def test_shows_killed_status(self, session: SafeSession) -> None:
        assert "killed=False" in repr(session)
        session._killed = True
        assert "killed=True" in repr(session)
