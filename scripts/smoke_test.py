#!/usr/bin/env python3
"""
OmniSight Production Smoke Test
================================
Validates that all key API endpoints are reachable and return expected
responses. Works against both dev (localhost:8000) and production URLs.

Usage:
    # Dev (default)
    python scripts/smoke_test.py

    # Production
    python scripts/smoke_test.py --url https://your-server --insecure

    # Custom credentials
    python scripts/smoke_test.py --url http://localhost:8000 --user admin --password admin

Exit codes:
    0 — all checks passed
    1 — one or more checks failed
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field

try:
    import requests
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
except ImportError:
    print("ERROR: 'requests' is not installed. Run: pip install requests")
    sys.exit(1)

# ── ANSI colours ──────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def ok(msg: str) -> str:
    return f"{GREEN}[PASS]{RESET} {msg}"


def fail(msg: str) -> str:
    return f"{RED}[FAIL]{RESET} {msg}"


def warn(msg: str) -> str:
    return f"{YELLOW}[SKIP]{RESET} {msg}"


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}-- {title} {'-' * max(0, 50 - len(title))}{RESET}")


# ── Result tracking ───────────────────────────────────────────────────────────
@dataclass
class SmokeResult:
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    failures: list[str] = field(default_factory=list)

    def record(self, name: str, success: bool, detail: str = "") -> None:
        # Strip non-ASCII to avoid cp1252 issues on Windows console
        safe_detail = detail.encode("ascii", "replace").decode("ascii") if detail else ""
        label = f"{name}" + (f" - {safe_detail}" if safe_detail else "")
        if success:
            self.passed += 1
            print(ok(label))
        else:
            self.failed += 1
            self.failures.append(label)
            print(fail(label))

    def skip(self, name: str, reason: str) -> None:
        self.skipped += 1
        print(warn(f"{name} [SKIP: {reason}]"))


# ── HTTP helpers ──────────────────────────────────────────────────────────────
class Smoker:
    def __init__(self, base_url: str, verify_ssl: bool, timeout: int = 10) -> None:
        self.base = base_url.rstrip("/")
        self.verify = verify_ssl
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = verify_ssl
        self._token: str | None = None

    def _headers(self) -> dict[str, str]:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def get(self, path: str, **kw) -> requests.Response:
        return self.session.get(
            f"{self.base}{path}",
            headers=self._headers(),
            timeout=self.timeout,
            **kw,
        )

    def post(self, path: str, **kw) -> requests.Response:
        return self.session.post(
            f"{self.base}{path}",
            headers=self._headers(),
            timeout=self.timeout,
            **kw,
        )

    def login(self, username: str, password: str) -> str | None:
        try:
            resp = self.session.post(
                f"{self.base}/api/v1/auth/login",
                data={"username": username, "password": password},
                timeout=self.timeout,
                verify=self.verify,
            )
            if resp.status_code == 200:
                self._token = resp.json().get("access_token")
                return self._token
        except Exception:
            pass
        return None


# ── Individual checks ─────────────────────────────────────────────────────────
def check_health(smoker: Smoker, result: SmokeResult) -> None:
    section("Health / Metrics")
    try:
        resp = smoker.get("/health")
        ok_status = resp.status_code == 200
        try:
            body = resp.json()
            is_ok = body.get("status") == "ok"
        except Exception:
            is_ok = False
        result.record("GET /health -> 200 + status=ok", ok_status and is_ok, f"HTTP {resp.status_code}")
    except Exception as exc:
        result.record("GET /health", False, str(exc))

    try:
        resp = smoker.get("/metrics")
        has_metrics = "omnisight_" in resp.text
        result.record(
            "GET /metrics -> 200 + omnisight_ metrics",
            resp.status_code == 200 and has_metrics,
            f"HTTP {resp.status_code}",
        )
    except Exception as exc:
        result.record("GET /metrics", False, str(exc))


def check_auth(smoker: Smoker, result: SmokeResult, username: str, password: str) -> bool:
    section("Authentication")
    # Unauthenticated access should be rejected
    try:
        resp = smoker.session.get(f"{smoker.base}/api/v1/employees", timeout=smoker.timeout, verify=smoker.verify)
        result.record("GET /employees without token -> 401", resp.status_code == 401, f"HTTP {resp.status_code}")
    except Exception as exc:
        result.record("GET /employees without token", False, str(exc))

    # Login
    try:
        token = smoker.login(username, password)
        result.record("POST /auth/login -> token received", token is not None)
        if not token:
            return False
    except Exception as exc:
        result.record("POST /auth/login", False, str(exc))
        return False

    # /auth/me
    try:
        resp = smoker.get("/api/v1/auth/me")
        ok_shape = resp.status_code == 200 and "username" in resp.json()
        result.record("GET /auth/me -> 200 + username field", ok_shape, f"HTTP {resp.status_code}")
    except Exception as exc:
        result.record("GET /auth/me", False, str(exc))

    return True


def check_employees(smoker: Smoker, result: SmokeResult) -> None:
    section("Employees")
    try:
        resp = smoker.get("/api/v1/employees")
        is_list = resp.status_code == 200 and isinstance(resp.json(), list)
        result.record(
            "GET /employees -> 200 list",
            is_list,
            f"HTTP {resp.status_code}, {len(resp.json()) if is_list else '?'} records",
        )
    except Exception as exc:
        result.record("GET /employees", False, str(exc))

    # Non-existent employee
    try:
        resp = smoker.get("/api/v1/employees/00000000-0000-0000-0000-000000000000")
        result.record("GET /employees/{invalid-id} -> 404", resp.status_code == 404, f"HTTP {resp.status_code}")
    except Exception as exc:
        result.record("GET /employees/{invalid-id}", False, str(exc))


def check_attendance(smoker: Smoker, result: SmokeResult) -> None:
    section("Attendance")
    try:
        resp = smoker.get("/api/v1/attendance?limit=10")
        is_list = resp.status_code == 200 and isinstance(resp.json(), list)
        result.record("GET /attendance?limit=10 -> 200 list", is_list, f"HTTP {resp.status_code}")
    except Exception as exc:
        result.record("GET /attendance", False, str(exc))

    try:
        resp = smoker.get("/api/v1/attendance/kpi")
        data = resp.json() if resp.status_code == 200 else {}
        has_keys = all(k in data for k in ("date", "today", "weekly", "by_dept"))
        result.record(
            "GET /attendance/kpi -> 200 + expected keys",
            resp.status_code == 200 and has_keys,
            f"HTTP {resp.status_code}",
        )
    except Exception as exc:
        result.record("GET /attendance/kpi", False, str(exc))

    try:
        resp = smoker.get("/api/v1/attendance/daily-report")
        data = resp.json() if resp.status_code == 200 else {}
        has_keys = all(k in data for k in ("date", "records", "late_threshold_minutes"))
        result.record(
            "GET /attendance/daily-report -> 200 + structure",
            resp.status_code == 200 and has_keys,
            f"HTTP {resp.status_code}",
        )
    except Exception as exc:
        result.record("GET /attendance/daily-report", False, str(exc))

    try:
        resp = smoker.get("/api/v1/attendance/summary")
        data = resp.json() if resp.status_code == 200 else {}
        has_keys = all(k in data for k in ("month", "total_records", "by_day", "by_department"))
        result.record(
            "GET /attendance/summary -> 200 + structure",
            resp.status_code == 200 and has_keys,
            f"HTTP {resp.status_code}",
        )
    except Exception as exc:
        result.record("GET /attendance/summary", False, str(exc))


def check_pdf_exports(smoker: Smoker, result: SmokeResult) -> None:
    section("PDF Exports")
    for _label, path in [
        ("daily-report PDF", "/api/v1/attendance/daily-report/pdf"),
        ("monthly summary PDF", "/api/v1/attendance/summary/pdf"),
    ]:
        try:
            resp = smoker.get(path)
            is_pdf = (
                resp.status_code == 200
                and resp.content[:4] == b"%PDF"
                and "application/pdf" in resp.headers.get("content-type", "")
            )
            result.record(f"GET {path} -> PDF bytes", is_pdf, f"HTTP {resp.status_code}, {len(resp.content)} bytes")
        except Exception as exc:
            result.record(f"GET {path}", False, str(exc))


def check_settings(smoker: Smoker, result: SmokeResult) -> None:
    section("Settings")
    try:
        resp = smoker.get("/api/v1/settings")
        is_list = resp.status_code == 200 and isinstance(resp.json(), list)
        result.record("GET /settings -> 200 list", is_list, f"HTTP {resp.status_code}")
    except Exception as exc:
        result.record("GET /settings", False, str(exc))


def check_stations(smoker: Smoker, result: SmokeResult) -> None:
    section("Stations")
    try:
        resp = smoker.get("/api/v1/stations")
        is_list = resp.status_code == 200 and isinstance(resp.json(), list)
        result.record("GET /stations -> 200 list", is_list, f"HTTP {resp.status_code}")
    except Exception as exc:
        result.record("GET /stations", False, str(exc))


def check_departments(smoker: Smoker, result: SmokeResult) -> None:
    section("Departments")
    try:
        resp = smoker.get("/api/v1/departments")
        is_list = resp.status_code == 200 and isinstance(resp.json(), list)
        result.record("GET /departments -> 200 list", is_list, f"HTTP {resp.status_code}")
    except Exception as exc:
        result.record("GET /departments", False, str(exc))


# ── Main ──────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="OmniSight production smoke test")
    p.add_argument("--url", default="http://localhost:8000", help="Base URL (default: http://localhost:8000)")
    p.add_argument("--user", default="admin", help="Admin username (default: admin)")
    p.add_argument("--password", default="admin", help="Admin password (default: admin)")
    p.add_argument("--insecure", action="store_true", help="Skip TLS certificate verification")
    p.add_argument("--timeout", type=int, default=15, help="Request timeout in seconds (default: 15)")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.insecure:
        requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

    print(f"\n{BOLD}OmniSight Smoke Test{RESET}")
    print(f"  Target : {CYAN}{args.url}{RESET}")
    print(f"  User   : {args.user}")
    print(f"  SSL    : {'skip verify' if args.insecure else 'verify'}")
    print(f"  Timeout: {args.timeout}s")

    smoker = Smoker(args.url, verify_ssl=not args.insecure, timeout=args.timeout)
    result = SmokeResult()
    t0 = time.time()

    # Run checks
    check_health(smoker, result)
    authed = check_auth(smoker, result, args.user, args.password)

    if authed:
        check_employees(smoker, result)
        check_attendance(smoker, result)
        check_pdf_exports(smoker, result)
        check_settings(smoker, result)
        check_stations(smoker, result)
        check_departments(smoker, result)
    else:
        skipped = ["employees", "attendance", "PDF exports", "settings", "stations", "departments"]
        for name in skipped:
            result.skip(name, "login failed")

    # Summary
    elapsed = time.time() - t0
    section("Summary")
    total = result.passed + result.failed
    print(f"  Passed : {GREEN}{result.passed}{RESET}/{total}")
    if result.failed:
        print(f"  Failed : {RED}{result.failed}{RESET}/{total}")
        for f in result.failures:
            print(f"    {RED}-{RESET} {f}")
    if result.skipped:
        print(f"  Skipped: {YELLOW}{result.skipped}{RESET}")
    print(f"  Time   : {elapsed:.1f}s")

    if result.failed == 0:
        print(f"\n{GREEN}{BOLD}All checks passed [OK]{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{BOLD}{result.failed} check(s) FAILED [FAIL]{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
