"""t09 — Failure recovery (bad params, insufficient gas, bad address)."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t09"
TEST_NAME = "failure_recovery"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("send_transaction", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的故障恢复能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    checks: list[dict] = []

    # Test 1: invalid address → should error cleanly
    try:
        bad_tx = TxParams(to="0xinvalid", value=0)
        result = await adapter.send_transaction(bad_tx)
        # If it didn't raise, check if the result indicates failure
        if result.tx_hash:
            checks.append({"test": "bad_address", "ok": False, "msg": "Unexpected success"})
        else:
            checks.append({"test": "bad_address", "ok": True, "msg": "Returned empty result"})
    except Exception as exc:
        checks.append({"test": "bad_address", "ok": True, "msg": f"Clean error: {exc}"})

    # Test 2: zero-address tx with absurdly high value (insufficient balance)
    try:
        huge_tx = TxParams(
            to="0x0000000000000000000000000000000000000001",
            value=10**30,  # way more than any testnet balance
        )
        result = await adapter.send_transaction(huge_tx)
        if result.tx_hash:
            checks.append({"test": "huge_value", "ok": False, "msg": "Unexpected success"})
        else:
            checks.append({"test": "huge_value", "ok": True, "msg": "Returned empty result"})
    except Exception as exc:
        checks.append({"test": "huge_value", "ok": True, "msg": f"Clean error: {exc}"})

    elapsed = (time.perf_counter() - t0) * 1000
    all_ok = all(c["ok"] for c in checks)

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if all_ok else TestStatus.FAIL,
        elapsed_ms=elapsed,
        message="所有故障场景均正常处理" if all_ok else "部分故障场景未正常处理",
        detail={"checks": checks},
    )
