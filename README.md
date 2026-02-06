<div align="center">

# socks5-killswitch

**Blocks all requests if your SOCKS5 proxy fails — no silent fallback.**

[![PyPI](https://img.shields.io/pypi/v/socks5-killswitch?color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/socks5-killswitch/)
[![Python](https://img.shields.io/pypi/pyversions/socks5-killswitch?logo=python&logoColor=white)](https://pypi.org/project/socks5-killswitch/)
[![License](https://img.shields.io/github/license/ponich/socks5-killswitch)](LICENSE)
[![CI](https://github.com/ponich/socks5-killswitch/actions/workflows/ci.yml/badge.svg)](https://github.com/ponich/socks5-killswitch/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?logo=codecov&logoColor=white)](#)
[![Typed](https://img.shields.io/badge/typing-PEP%20561-blue?logo=python&logoColor=white)](#)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000?logo=ruff&logoColor=white)](https://docs.astral.sh/ruff/)

---

SOCKS5 proxy session for Python built on `requests.Session`.<br>
If the proxy drops — all requests are **instantly killed**. No silent fallback to your real IP.

</div>

## The Problem

Standard `requests` + SOCKS5 proxy setup has a fatal flaw: if the proxy goes down, requests silently fall back to your **real IP**. You're exposed and don't even know it.

## The Solution

```
              Request ──► Proxy OK? ──► Yes ──► Send through proxy
                              │
                              No
                              │
                         KILL SWITCH ON
                              │
                    ┌─────────┴─────────┐
                    │  All requests      │
                    │  blocked forever   │
                    │  ProxyError raised │
                    └───────────────────┘
```

## Install

```bash
pip install socks5-killswitch
```

## Quick Start

```python
from socks5_killswitch import create_session, ProxyError

# Create a protected session — real IP is detected and verified automatically
session = create_session(
    host="proxy.example.com",
    port=1080,
    username="your-socks5-user",
    password="your-socks5-pass",
)

# All requests go through the proxy — just like normal requests.Session
resp = session.get("https://example.com")

# Periodic leak check — verifies visible IP != real IP
session.check_ip()

# If proxy ever fails:
# ❌ ProxyError raised
# ❌ ALL further requests blocked
# ❌ No fallback to direct connection
# ✅ Your real IP is not exposed through this session
```

## How It Works

| Event | What happens |
|-------|-------------|
| `create_session()` | Detects real IP via [ipify.org](https://www.ipify.org), connects through proxy, verifies proxy IP is different |
| Successful request | Passes through proxy as normal |
| **Any** request failure | Kill switch activates — `_killed = True`, `ProxyError` raised |
| Subsequent requests | Instantly raise `ProxyError` — zero network calls |
| `check_ip()` | Preflight TCP check → verifies visible IP != real IP (works even after kill switch!) |

## API

### `create_session(host, port, username, password, **kwargs)`

Factory that returns a verified `SafeSession`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `host` | `str` | — | SOCKS5 proxy host |
| `port` | `int` | — | SOCKS5 proxy port |
| `username` | `str` | — | SOCKS5 username |
| `password` | `str` | — | SOCKS5 password |
| `timeout` | `int` | `15` | Default request timeout (seconds) |
| `ip_check_url` | `str` | `https://api.ipify.org` | IP detection service URL |
| `preflight` | `bool` | `True` | TCP-check proxy reachability before IP verification |

### `SafeSession`

Extends `requests.Session` with kill switch protection.

```python
session.get(url)              # proxied request, kills on failure
session.post(url, data=b"…")  # binary data works (AMF2, protobuf, etc.)
session.check_ip()            # returns proxy IP or raises ProxyError
repr(session)                 # <SafeSession proxy=socks5://user:***@host:1080 killed=False>
```

### `ProxyError`

Raised when proxy fails or IP leak is detected. Original exception is chained via `__cause__`.

## Security Model

### What the kill switch covers

- **Proxy failure → instant block** — if any request through the proxy raises an exception, the session is permanently locked. No fallback to a direct connection, ever.
- **IP verification on startup** — `create_session()` detects your real IP, connects through the proxy, and confirms the proxy IP is different before returning the session.
- **On-demand leak detection** — `check_ip()` verifies your visible IP hasn't changed. Call it periodically in long-running sessions.

### What is outside the scope

This is **application-level** protection for a single `requests.Session`. It does not cover:

- **DNS queries** — uses `socks5://` by default (local DNS resolution). Your ISP can see which domains you visit. See [#1](https://github.com/ponich/socks5-killswitch/issues/1).
- **Requests outside `SafeSession`** — a plain `requests.get()` elsewhere in your code goes direct.
- **Non-HTTP traffic** — WebSocket, UDP, raw sockets are not routed through the proxy.
- **OS-level enforcement** — other processes and applications are not affected.

For maximum protection, combine this library with a VPN or firewall rules that block non-proxied outbound traffic.

## Design Decisions

- **`socks5://` not `socks5h://`** — DNS is resolved locally (required for PIA and similar providers)
- **Pure library** — no `.env`, no config files, no side effects. All parameters passed explicitly
- **`check_ip()` bypasses kill switch** — intentional; leak detection must work even in degraded state
- **Preflight TCP check** — `check_ip()` verifies proxy is TCP-reachable before hitting ipify, preventing real IP leak to external services
- **Password masked in `repr()`** — `socks5://user:***@host:1080`, safe for logging

## License

[MIT](LICENSE)
