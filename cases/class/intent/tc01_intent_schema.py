"""tc01 (intent) — Malformed intent / boundary values → local validation."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "tc01"
TEST_NAME = "intent_schema"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("send_transaction", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的意图 Schema 能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    checks: list[dict] = []

    # Test 1: empty 'to' address
    try:
        bad_tx = TxParams(to="", value=0)
        result = await adapter.send_transaction(bad_tx)
        checks.append({
            "test": "empty_to",
            "ok": not result.tx_hash,
            "msg": "Returned empty result" if not result.tx_hash else "Unexpected success",
        })
    except Exception as exc:
        checks.append({"test": "empty_to", "ok": True, "msg": f"Rejected: {exc}"})

    # Test 2: malformed address
    try:
        bad_tx = TxParams(to="not-an-address", value=100)
        result = await adapter.send_transaction(bad_tx)
        checks.append({
            "test": "malformed_to",
            "ok": not result.tx_hash,
            "msg": "Returned empty result" if not result.tx_hash else "Unexpected success",
        })
    except Exception as exc:
        checks.append({"test": "malformed_to", "ok": True, "msg": f"Rejected: {exc}"})

    # Test 3: negative value (boundary)
    try:
        bad_tx = TxParams(to="0x0000000000000000000000000000000000000001", value=-1)
        result = await adapter.send_transaction(bad_tx)
        checks.append({
            "test": "negative_value",
            "ok": not result.tx_hash,
            "msg": "Returned empty result" if not result.tx_hash else "Unexpected success",
        })
    except Exception as exc:
        checks.append({"test": "negative_value", "ok": True, "msg": f"Rejected: {exc}"})

    elapsed = (time.perf_counter() - t0) * 1000
    all_ok = all(c["ok"] for c in checks)

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if all_ok else TestStatus.FAIL,
        elapsed_ms=elapsed,
        message="所有异常意图已拒绝" if all_ok else "部分异常意图被接受",
        detail={"checks": checks},
    )
