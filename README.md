# py-vpn-wrapper

SOCKS5 proxy wrapper for Python with **kill switch** — if the proxy drops, your real IP is never exposed.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env
# fill in SOCKS5 credentials in .env
```

## Usage

```python
from proxy import create_session, ProxyError

session = create_session(
    host="proxy-nl.privateinternetaccess.com",
    port=1080,
    username="your-socks5-user",
    password="your-socks5-pass",
)

# all requests go through proxy
resp = session.get("https://example.com")

# periodic leak check
session.check_ip()

# if proxy fails — ProxyError is raised, all further requests blocked
```

## How kill switch works

1. On `create_session()` — detects real IP, verifies proxy gives a different one
2. On any request failure — instantly blocks ALL further requests (no fallback to direct)
3. `check_ip()` — manual/periodic check that visible IP != real IP

## Demo

```bash
.venv/bin/python get_my_ip.py
```
