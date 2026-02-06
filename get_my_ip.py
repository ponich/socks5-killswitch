#!/usr/bin/env python3
"""Demo: client reads .env itself, passes values to proxy lib."""

import requests
from pathlib import Path
from proxy import create_session, ProxyError


def load_env():
    env = {}
    for line in (Path(__file__).parent / ".env").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        if value:
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def main():
    env = load_env()

    session = create_session(
        host=env["SOCKS5_HOST"],
        port=int(env["SOCKS5_PORT"]),
        username=env["SOCKS5_USERNAME"],
        password=env["SOCKS5_PASSWORD"],
    )

    ip = session.get("https://api.ipify.org").text
    print(f"Request OK: {ip}")

    session.check_ip()
    print("IP check OK")

    # kill switch test
    print("\n--- Kill switch test ---")
    session._killed = True
    try:
        session.get("https://api.ipify.org")
    except ProxyError as e:
        print(f"Blocked: {e}")


if __name__ == "__main__":
    main()
