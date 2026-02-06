from __future__ import annotations

import socket
from unittest.mock import patch

import responses

from socks5_killswitch import SafeSession, create_session, force_ipv4

from .conftest import IP_CHECK_URL, PROXY_IP, PROXY_URL, REAL_IP


class TestForceIpv4:
    def test_patches_getaddrinfo(self) -> None:
        """force_ipv4() replaces socket.getaddrinfo."""
        import socks5_killswitch

        socks5_killswitch._ipv4_forced = False
        original = socket.getaddrinfo
        try:
            force_ipv4()
            assert socket.getaddrinfo is not original
        finally:
            socket.getaddrinfo = original  # type: ignore[assignment]
            socks5_killswitch._ipv4_forced = False

    def test_idempotent(self) -> None:
        """Calling force_ipv4() twice doesn't double-patch."""
        import socks5_killswitch

        socks5_killswitch._ipv4_forced = False
        original = socket.getaddrinfo
        try:
            force_ipv4()
            patched = socket.getaddrinfo
            force_ipv4()
            assert socket.getaddrinfo is patched
        finally:
            socket.getaddrinfo = original  # type: ignore[assignment]
            socks5_killswitch._ipv4_forced = False

    def test_forces_af_inet(self) -> None:
        """Patched getaddrinfo always passes AF_INET."""
        import socks5_killswitch

        socks5_killswitch._ipv4_forced = False
        original = socket.getaddrinfo
        try:
            force_ipv4()
            with patch.object(
                socks5_killswitch, "_original_getaddrinfo"
            ) as mock_gai:
                mock_gai.return_value = []
                socket.getaddrinfo("example.com", 80)
                mock_gai.assert_called_once_with(
                    "example.com", 80, socket.AF_INET, 0, 0, 0,
                )
        finally:
            socket.getaddrinfo = original  # type: ignore[assignment]
            socks5_killswitch._ipv4_forced = False


class TestIpv4OnlyParam:
    def test_session_calls_force_ipv4(self) -> None:
        """SafeSession(ipv4_only=True) calls force_ipv4()."""
        with patch("socks5_killswitch.force_ipv4") as mock:
            SafeSession(PROXY_URL, REAL_IP, preflight=False, ipv4_only=True)
            mock.assert_called_once()

    def test_session_skips_without_flag(self) -> None:
        """SafeSession(ipv4_only=False) does not call force_ipv4()."""
        with patch("socks5_killswitch.force_ipv4") as mock:
            SafeSession(PROXY_URL, REAL_IP, preflight=False, ipv4_only=False)
            mock.assert_not_called()

    @responses.activate
    def test_create_session_with_ipv4_only(self) -> None:
        """create_session(ipv4_only=True) calls force_ipv4()."""
        responses.get(IP_CHECK_URL, body=REAL_IP)
        responses.get(IP_CHECK_URL, body=PROXY_IP)
        with patch("socks5_killswitch.force_ipv4") as mock:
            create_session(
                "host", 1080, "user", "pass",
                preflight=False, ipv4_only=True,
            )
            mock.assert_called()

    def test_stored_as_attribute(self) -> None:
        """ipv4_only flag is stored on the session."""
        s = SafeSession(PROXY_URL, REAL_IP, preflight=False, ipv4_only=True)
        assert s._ipv4_only is True
