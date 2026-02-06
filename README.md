# socks5-killswitch

SOCKS5 proxy session for Python with **kill switch** — if the proxy drops, your real IP is never exposed.

Built on top of `requests.Session`. If any request fails, the session permanently blocks all further requests instead of falling back to a direct connection.

## Install

```bash
pip install socks5-killswitch
```

## Quick start

```python
from socks5_killswitch import create_session, ProxyError

session = create_session(
    host="proxy.example.com",
    port=1080,
    username="your-socks5-user",
    password="your-socks5-pass",
)

# All requests go through the proxy
resp = session.get("https://example.com")

# Periodic leak check — verifies visible IP != real IP
session.check_ip()

# If proxy fails — ProxyError is raised, all further requests blocked
```

## How the kill switch works

1. **On `create_session()`** — detects your real IP, verifies the proxy gives a different one.
2. **On any request failure** — instantly blocks ALL further requests (no fallback to direct).
3. **`check_ip()`** — manual/periodic check that visible IP != real IP.

## API

### `create_session(host, port, username, password, timeout=15, ip_check_url=...)`

Factory that returns a verified `SafeSession`. Raises `ProxyError` if the proxy is unreachable or the IP leaks.

### `SafeSession`

Extends `requests.Session`. Every request goes through the SOCKS5 proxy. On failure, the kill switch activates and all subsequent calls raise `ProxyError`.

- `check_ip() -> str` — verify the session is behind the proxy. Returns the visible IP.
- `_killed: bool` — kill switch state (read-only in practice).

### `ProxyError`

Raised when the proxy fails or an IP leak is detected.

## Notes

- Uses `socks5://` (not `socks5h://`) — DNS is resolved locally.
- Supports binary POST data (e.g. AMF2 payloads).
- Pure library — no `.env`, no config files. All parameters are passed explicitly.

## License

MIT
