"""t38 — Version compatibility: verify adapter reports version and key APIs work."""
from __future__ import annotations

import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t38"
TEST_NAME = "version_compat"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Check adapter metadata and smoke-test key interfaces.

    Verifies:
    1. adapter.name is non-empty
    2. adapter.arch_class is valid
    3. adapter.chains is non-empty
    4. capabilities() returns a dict with expected keys
    5. create_wallet() succeeds (basic smoke)
    """
    t0 = time.perf_counter()

    checks_passed = 0
    checks_total = 0
    issues: list[str] = []

    # Check 1: adapter.name
    checks_total += 1
    if adapter.name:
        checks_passed += 1
    else:
        issues.append("adapter.name is empty")

    # Check 2: adapter.arch_class
    checks_total += 1
    valid_classes = {"local", "api_custodial", "intent", "tee", "mpc_aa"}
    if adapter.arch_class in valid_classes:
        checks_passed += 1
    else:
        issues.append(f"adapter.arch_class='{adapter.arch_class}' not in {valid_classes}")

    # Check 3: adapter.chains
    checks_total += 1
    if adapter.chains:
        checks_passed += 1
    else:
        issues.append("adapter.chains is empty")

    # Check 4: capabilities()
    checks_total += 1
    caps = adapter.capabilities()
    expected_keys = {"create_wallet", "sign_message", "send_transaction"}
    if isinstance(caps, dict) and expected_keys.issubset(caps.keys()):
        checks_passed += 1
    else:
        missing = expected_keys - set(caps.keys()) if isinstance(caps, dict) else expected_keys
        issues.append(f"capabilities() missing keys: {missing}")

    # Check 5: create_wallet smoke
    checks_total += 1
    try:
        wallet = await adapter.create_wallet()
        if wallet.address:
            checks_passed += 1
        else:
            issues.append("create_wallet() returned empty address")
    except Exception as exc:
        issues.append(f"create_wallet() failed: {str(exc)[:120]}")

    elapsed = (time.perf_counter() - t0) * 1000

    detail: dict[str, Any] = {
        "checks_passed": checks_passed,
        "checks_total": checks_total,
        "adapter_name": adapter.name,
        "arch_class": adapter.arch_class,
        "chains_count": len(adapter.chains),
        "capabilities_count": len(caps) if isinstance(caps, dict) else 0,
    }
    if issues:
        detail["issues"] = issues

    if checks_passed == checks_total:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=f"所有 {checks_total} 项兼容性检查通过 (name={adapter.name}, arch={adapter.arch_class})",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=f"兼容性检查 {checks_passed}/{checks_total} 通过: {'; '.join(issues[:3])}",
        detail=detail,
        owner="provider",
    )
