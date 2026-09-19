#!/usr/bin/env python3
"""
ClaimSaathi Automated Smoke Test Script
Tests the full auth lifecycle and connectivity against either local or deployed URL:
1. GET /health
2. GET /ready
3. POST /api/v1/auth/register
4. POST /api/v1/auth/login
5. POST /api/v1/auth/refresh
6. GET /api/v1/auth/me
7. POST /api/v1/auth/logout

Usage:
  python scripts/smoke_test.py [BASE_URL]
  Default: http://localhost:8000 (or pass https://claimsaathi.onrender.com)
"""
import sys
import time
import uuid
import urllib.request
import urllib.error
import json
import ssl

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
BASE_URL = BASE_URL.rstrip("/")
ctx = ssl.create_default_context()

print("=" * 60)
print(f" ClaimSaathi Smoke Test Suite -> {BASE_URL}")
print("=" * 60)

passed = 0
failed = 0

def log_test(name: str, success: bool, detail: str = ""):
    global passed, failed
    if success:
        passed += 1
        print(f" [PASS] {name} {detail}")
    else:
        failed += 1
        print(f" [FAIL] {name} - {detail}")

def http_req(path: str, method: str = "GET", body: dict = None, token: str = None):
    url = f"{BASE_URL}{path}"
    headers = {"User-Agent": "ClaimSaathi-SmokeTest/1.0"}
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            resp_body = resp.read().decode("utf-8")
            parsed = json.loads(resp_body) if resp_body else {}
            return resp.status, parsed
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode("utf-8")
        try:
            parsed = json.loads(resp_body)
        except Exception:
            parsed = {"raw": resp_body}
        return e.code, parsed
    except Exception as e:
        return 0, {"error": str(e)}

# 1. Health Check
status, data = http_req("/health")
log_test("1. GET /health", status == 200, f"(status: {status}, response: {data})")

# 2. Readiness Check
status, data = http_req("/ready")
log_test("2. GET /ready", status in (200, 503), f"(status: {status}, response: {data.get('status', data)})")

# 3. Register a test user
test_email = f"smoketest_{uuid.uuid4().hex[:8]}@example.com"
test_pwd = "SmokePass@2026!"
status, data = http_req("/api/v1/auth/register", method="POST", body={
    "email": test_email,
    "password": test_pwd,
    "full_name": "Smoke Test Runner"
})
access_token = data.get("access_token")
refresh_token = data.get("refresh_token")
log_test("3. POST /api/v1/auth/register", status == 201 or status == 200, f"(status: {status}, user: {test_email})")

# 4. Login with registered user
if status in (200, 201):
    status, login_data = http_req("/api/v1/auth/login", method="POST", body={
        "email": test_email,
        "password": test_pwd
    })
    access_token = login_data.get("access_token", access_token)
    refresh_token = login_data.get("refresh_token", refresh_token)
    log_test("4. POST /api/v1/auth/login", status == 200, f"(status: {status}, token received: {bool(access_token)})")
else:
    log_test("4. POST /api/v1/auth/login", False, "Skipped due to registration failure (DB may be offline)")

# 5. Refresh token
if refresh_token:
    status, refresh_data = http_req("/api/v1/auth/refresh", method="POST", body={
        "refresh_token": refresh_token
    })
    new_access = refresh_data.get("access_token")
    log_test("5. POST /api/v1/auth/refresh", status == 200 and bool(new_access), f"(status: {status})")
    if new_access:
        access_token = new_access
else:
    log_test("5. POST /api/v1/auth/refresh", False, "No refresh token available")

# 6. Current user /auth/me
if access_token:
    status, me_data = http_req("/api/v1/auth/me", token=access_token)
    log_test("6. GET /api/v1/auth/me", status == 200, f"(status: {status}, email: {me_data.get('email')})")
else:
    log_test("6. GET /api/v1/auth/me", False, "No access token available")

# 7. Logout
if refresh_token and access_token:
    status, logout_data = http_req("/api/v1/auth/logout", method="POST", body={
        "refresh_token": refresh_token
    }, token=access_token)
    log_test("7. POST /api/v1/auth/logout", status in (200, 204), f"(status: {status})")
else:
    log_test("7. POST /api/v1/auth/logout", False, "No active session to logout")

print("=" * 60)
print(f" Summary: {passed} passed, {failed} failed")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
