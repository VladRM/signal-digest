#!/usr/bin/env python3
"""One-shot check for twitterapi.io access."""
import os
import sys

import requests


DEFAULT_HANDLE = "AnthropicAI"


def main() -> int:
    api_key = os.getenv("TWITTER_API_KEY")
    if not api_key:
        print("TWITTER_API_KEY is not set.")
        return 2

    handle = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HANDLE
    url = "https://api.twitterapi.io/twitter/user/last_tweets"
    headers = {"X-API-Key": api_key}
    params = {"userName": handle}

    print(f"GET {url}")
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
    except requests.RequestException as exc:
        print(f"Request failed: {exc}")
        return 1

    print(f"Status: {response.status_code}")
    if response.ok:
        print("OK")
        return 0

    body = response.text[:400].replace("\n", "\\n")
    print(f"Body: {body}")
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
