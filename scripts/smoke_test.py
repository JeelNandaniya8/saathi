#!/usr/bin/env python3
"""Read-only production smoke checks for a deployed Saathi URL."""

import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


EXPECTED_RELEASE = "2026-08-30-ai-experience"


def fetch(base_url, path, timeout):
    request = Request(
        base_url.rstrip("/") + path,
        headers={"User-Agent": "Saathi-Smoke-Test/1.0", "Accept": "application/json,text/html"},
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return response.status, response.read(), dict(response.headers)
    except HTTPError as error:
        return error.code, error.read(), dict(error.headers)


def run(base_url, timeout, expected_release=EXPECTED_RELEASE):
    failures = []

    for path in ("/", "/privacy", "/terms", "/limitations", "/support"):
        status, _body, headers = fetch(base_url, path, timeout)
        if status != 200:
            failures.append(f"{path} returned {status}, expected 200")
        if headers.get("X-Content-Type-Options") != "nosniff":
            failures.append(f"{path} is missing X-Content-Type-Options: nosniff")

    status, body, _headers = fetch(base_url, "/api/health", timeout)
    try:
        health = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        health = {}
    if status != 200 or health.get("status") != "ok":
        failures.append(f"/api/health returned {status} with status={health.get('status')!r}")
    if expected_release and health.get("release") != expected_release:
        failures.append(
            f"/api/health returned release={health.get('release')!r}, "
            f"expected {expected_release!r}"
        )

    status, body, _headers = fetch(base_url, "/api/plans", timeout)
    try:
        plans = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        plans = {}
    if status != 200 or plans.get("checkout_enabled") is not False:
        failures.append("/api/plans must be available with checkout_enabled=false")

    for path in ("/app.py", "/README.md", "/requirements.txt", "/.env", "/.git/config"):
        status, _body, _headers = fetch(base_url, path, timeout)
        if status != 404:
            failures.append(f"{path} returned {status}, expected 404")

    return failures


def main():
    parser = argparse.ArgumentParser(description="Run read-only checks against a deployed Saathi site.")
    parser.add_argument("base_url", help="Deployment URL, for example https://saathi-md5w.onrender.com")
    parser.add_argument("--timeout", type=float, default=60, help="Seconds to wait for each request")
    parser.add_argument(
        "--expected-release",
        default=EXPECTED_RELEASE,
        help="Release ID expected from /api/health (use an empty value to skip this check)",
    )
    args = parser.parse_args()
    try:
        failures = run(args.base_url, args.timeout, args.expected_release)
    except (URLError, TimeoutError) as error:
        print(f"Smoke test could not connect: {error}", file=sys.stderr)
        return 1
    if failures:
        for failure in failures:
            print(f"FAIL: {failure}", file=sys.stderr)
        return 1
    print("Saathi smoke checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
