"""SOCKS5 proxy session with IP leak protection (kill switch).

Pure library — no .env, no config files. All params from caller.
"""

import requests
from requests.exceptions import RequestException


_TIMEOUT = 15
_IP_CHECK_URL = "https://api.ipify.org"


class ProxyError(Exception):
    """Proxy is down. All requests blocked until reconnect."""


class SafeSession(requests.Session):
    """Session with kill switch — blocks all requests if proxy fails."""

    def __init__(self, proxy_url, real_ip, timeout=_TIMEOUT):
        super().__init__()
        self.proxies = {"http": proxy_url, "https": proxy_url}
        self.timeout = timeout
        self._proxy_url = proxy_url
        self._real_ip = real_ip
        self._killed = False

    def request(self, method, url, **kwargs):
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

    def check_ip(self):
        """Verify we're behind proxy. Raises ProxyError if real IP leaks."""
        try:
            visible_ip = super().request("GET", _IP_CHECK_URL, timeout=10).text.strip()
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


def create_session(host, port, username, password, timeout=_TIMEOUT):
    """Create a safe SOCKS5 session. Verifies proxy before returning.

    Args:
        host:     SOCKS5 proxy host
        port:     SOCKS5 proxy port
        username: SOCKS5 username
        password: SOCKS5 password
        timeout:  default request timeout (seconds)

    Returns:
        SafeSession routed through proxy.

    Raises:
        ProxyError: if proxy is unreachable or IP leaks.
    """
    proxy_url = f"socks5://{username}:{password}@{host}:{port}"

    real_ip = requests.get(_IP_CHECK_URL, timeout=10).text.strip()
    session = SafeSession(proxy_url, real_ip, timeout)

    proxy_ip = session.check_ip()
    print(f"Proxy OK: {proxy_ip}  (real: {real_ip})")

    return session
