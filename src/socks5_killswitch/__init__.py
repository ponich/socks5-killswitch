"""SOCKS5 proxy session with IP leak protection (kill switch).

Pure library — no .env, no config files. All params from caller.
"""

from __future__ import annotations

import logging
import re
import socket
from typing import Any
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException

__all__ = ["ProxyError", "SafeSession", "create_session", "force_ipv4"]
__version__ = "0.0.4"

_TIMEOUT = 15
_IP_CHECK_URL = "https://api.ipify.org"

logger = logging.getLogger(__name__)

_original_getaddrinfo = socket.getaddrinfo
_ipv4_forced = False


class ProxyError(Exception):
    """Proxy is down. All requests blocked until reconnect."""


def force_ipv4() -> None:
    """Monkey-patch ``socket.getaddrinfo`` to return only IPv4 (AF_INET) results.

    Many SOCKS5 proxies (e.g. PIA) don't support IPv6.  When a hostname resolves
    to an IPv6 address first, the proxy rejects it with "Address type not
    supported".  This function forces all DNS resolution to IPv4.

    Safe to call multiple times — only patches once.
    """
    global _ipv4_forced
    if _ipv4_forced:
        return

    def _ipv4_getaddrinfo(
        host: Any,
        port: Any,
        family: int = 0,
        type: int = 0,
        proto: int = 0,
        flags: int = 0,
    ) -> list[Any]:
        return _original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = _ipv4_getaddrinfo
    _ipv4_forced = True
    logger.debug("socket.getaddrinfo patched to force IPv4")


class SafeSession(requests.Session):
    """Session with kill switch — blocks all requests if proxy fails.

    Wraps every request: on any ``RequestException`` the kill switch activates
    and all subsequent calls raise ``ProxyError`` immediately — no fallback to
    a direct connection.

    Args:
        proxy_url: Full SOCKS5 URL, e.g. ``socks5://user:pass@host:1080``.
        real_ip: The machine's real public IP (used for leak detection).
        timeout: Default request timeout in seconds.
        ip_check_url: URL that returns the caller's IP as plain text.
        preflight: If True, verify proxy is TCP-reachable before IP checks.
        ipv4_only: If True, force all DNS resolution to IPv4 via
            :func:`force_ipv4`.  Required for SOCKS5 proxies that don't
            support IPv6 (e.g. PIA, NordVPN).
    """

    def __init__(
        self,
        proxy_url: str,
        real_ip: str,
        timeout: int = _TIMEOUT,
        ip_check_url: str = _IP_CHECK_URL,
        preflight: bool = True,
        ipv4_only: bool = False,
    ) -> None:
        super().__init__()
        if ipv4_only:
            force_ipv4()
        self.proxies = {"http": proxy_url, "https": proxy_url}
        self.timeout = timeout
        self._proxy_url = proxy_url
        self._real_ip = real_ip
        self._killed = False
        self._ip_check_url = ip_check_url
        self._preflight = preflight
        self._ipv4_only = ipv4_only

    def request(self, method: str | bytes, url: str | bytes, **kwargs: Any) -> requests.Response:  # type: ignore[override]
        """Send a request through the proxy.

        Raises:
            ProxyError: If the kill switch is active or the request fails.
        """
        if self._killed:
            raise ProxyError(
                "Kill switch active — proxy was lost. "
                "Create a new session to reconnect."
            )
        kwargs.setdefault("timeout", self.timeout)
        try:
            return super().request(method, url, **kwargs)
        except RequestException as e:
            self._killed = True
            raise ProxyError(f"Proxy failed, kill switch ON: {e}") from e

    def check_ip(self) -> str:
        """Verify the session is behind the proxy.

        Uses ``super().request()`` to bypass the kill switch guard — this is
        intentional so leak detection works even in a degraded state.

        Returns:
            The visible (proxy) IP address.

        Raises:
            ProxyError: If the real IP is exposed or the check fails.
        """
        if self._preflight:
            parsed = urlparse(self._proxy_url)
            port = parsed.port or 1080
            try:
                sock = socket.create_connection(
                    (parsed.hostname, port), timeout=5,
                )
                sock.close()
            except OSError as e:
                self._killed = True
                raise ProxyError(f"Proxy unreachable, kill switch ON: {e}") from e

        try:
            visible_ip = (
                super().request("GET", self._ip_check_url, timeout=10).text.strip()
            )
        except RequestException as e:
            self._killed = True
            raise ProxyError(f"IP check failed, kill switch ON: {e}") from e

        if visible_ip == self._real_ip:
            self._killed = True
            raise ProxyError(
                f"LEAK DETECTED: visible IP {visible_ip} == real IP. "
                "Kill switch ON."
            )
        return visible_ip

    def __repr__(self) -> str:
        parsed = urlparse(self._proxy_url)
        masked = re.sub(
            r"://([^:]+):[^@]+@",
            r"://\1:***@",
            parsed.geturl(),
        )
        return f"<SafeSession proxy={masked} killed={self._killed}>"


def create_session(
    host: str,
    port: int,
    username: str,
    password: str,
    timeout: int = _TIMEOUT,
    ip_check_url: str = _IP_CHECK_URL,
    preflight: bool = True,
    ipv4_only: bool = False,
) -> SafeSession:
    """Create a safe SOCKS5 session. Verifies the proxy before returning.

    Args:
        host: SOCKS5 proxy host.
        port: SOCKS5 proxy port.
        username: SOCKS5 username.
        password: SOCKS5 password.
        timeout: Default request timeout in seconds.
        ip_check_url: URL that returns the caller's IP as plain text.
        preflight: If True, verify proxy is TCP-reachable before IP checks.
        ipv4_only: If True, force all DNS resolution to IPv4.  Required for
            SOCKS5 proxies that don't support IPv6 (e.g. PIA, NordVPN).

    Returns:
        A ``SafeSession`` routed through the proxy.

    Raises:
        ProxyError: If the proxy is unreachable or the IP leaks.
    """
    if ipv4_only:
        force_ipv4()

    proxy_url = f"socks5://{username}:{password}@{host}:{port}"

    real_ip = requests.get(ip_check_url, timeout=10).text.strip()
    session = SafeSession(
        proxy_url, real_ip, timeout, ip_check_url, preflight, ipv4_only=ipv4_only,
    )

    proxy_ip = session.check_ip()
    logger.info("Proxy OK: %s  (real: %s)", proxy_ip, real_ip)

    return session
