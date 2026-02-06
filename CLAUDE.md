# py-vpn-wrapper

SOCKS5 proxy library with IP leak protection (kill switch).

## Structure

- `proxy.py` — library, pure API, no config knowledge. Accepts host/port/user/pass from caller.
- `get_my_ip.py` — demo/test client.
- `.env` — client-side config (gitignored), see `.env.example`.

## Key design decisions

- `proxy.py` is a library: no .env, no file I/O, no hardcoded values.
- Kill switch: any proxy failure blocks all subsequent requests. No fallback to direct connection.
- `check_ip()` compares visible IP against real IP detected at session creation.
- Uses `socks5://` (local DNS) not `socks5h://` — PIA proxy doesn't resolve DNS.

## Run

```
.venv/bin/python get_my_ip.py
```

## Dependencies

PySocks, requests — installed in .venv.
