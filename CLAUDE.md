# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# setup
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

# run tests
.venv/bin/pytest tests/ -v

# run tests with coverage
.venv/bin/pytest tests/ -v --cov=socks5_killswitch

# lint
.venv/bin/ruff check src tests

# type check
.venv/bin/mypy src

# build package
.venv/bin/pip install hatch
.venv/bin/hatch build

# run demo (requires .env with SOCKS5 credentials)
.venv/bin/python examples/get_my_ip.py
```

## Architecture

`src/socks5_killswitch/__init__.py` is a **pure library** — no .env, no file I/O, no config knowledge. All parameters (host, port, username, password) are passed explicitly by the caller.

**Entry point:** `create_session(host, port, username, password)` → returns `SafeSession`.

**SafeSession** extends `requests.Session` with a kill switch:
- Every request is wrapped: on any `RequestException`, `_killed` is set to `True` and all subsequent requests raise `ProxyError` immediately — no fallback to direct connection.
- `check_ip()` verifies visible IP != real IP (detected once at session creation via ipify.org). Mismatch triggers kill switch.
- `check_ip()` calls `super().request()` to bypass the kill switch guard (intentional — it needs to work even in degraded state to detect leaks).

**Client code** (e.g. `examples/get_my_ip.py`) is responsible for loading config from wherever it wants (.env, args, DB) and passing values to the library.

## Key constraints

- Uses `socks5://` not `socks5h://` — PIA's proxy doesn't resolve DNS, local DNS resolution is required.
- PIA SOCKS5 credentials are **separate** from VPN credentials — generated at PIA control panel.
- The project handles AMF2 binary payloads over HTTP/HTTPS — `session.post(url, data=binary_bytes)` must work with arbitrary content types.
- `ip_check_url` parameter allows overriding the default ipify.org endpoint (useful for testing and alternative services).

## Testing

Tests use `pytest` + `responses` library to mock HTTP at the transport level — no real proxy needed. Test files:
- `tests/test_session.py` — SafeSession init, request routing, kill switch activation
- `tests/test_check_ip.py` — IP leak detection, kill switch bypass
- `tests/test_create_session.py` — factory function, logging, error handling
