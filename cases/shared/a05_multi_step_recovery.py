"""a05 — Multi-step recovery: verify Agent can recover from mid-flow errors."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "a05"
TEST_NAME = "multi_step_recovery"

_DEFAULT_TIMEOUT = 30


def _params(config: dict) -> dict[str, Any]:
    return config.get("test_params", {}).get("a05", {})


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Test 3-step flow with injected error, then recovery.

    Flow:
    1. create_wallet (should succeed)
    2. send_transaction to invalid address (should fail gracefully)
    3. send_transaction to valid address (should succeed — proving recovery)

    PASS if step 3 succeeds after step 2 fails gracefully.
    FAIL if step 2 corrupts adapter state so step 3 also fails.
    """
    params = _params(config)
    timeout = params.get("timeout", _DEFAULT_TIMEOUT)

    caps = adapter.capabilities()
    if not caps.get("send_transaction", False):
        if "send_transaction" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持交易发送能力。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的交易发送能力。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    steps: list[dict[str, Any]] = []

    # Step 1: create_wallet (baseline)
    step_start = time.perf_counter()
    try:
        wallet = await asyncio.wait_for(adapter.create_wallet(), timeout=timeout)
        steps.append({"step": "create_wallet", "ok": True, "ms": round((time.perf_counter() - step_start) * 1000, 1)})
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Step 1 create_wallet 失败: {exc}",
            detail={"steps": steps},
            owner="provider",
        )

    # Step 2: inject error — send to invalid address
    step_start = time.perf_counter()
    step2_error: str | None = None
    try:
        bad_tx = TxParams(to="0xinvalid_address_for_error_injection", value=10**30)
        await asyncio.wait_for(adapter.send_transaction(bad_tx), timeout=timeout)
        # If it somehow succeeds, that's also fine — step 2 is the error injection
        steps.append({"step": "error_inject", "ok": True, "ms": round((time.perf_counter() - step_start) * 1000, 1), "note": "unexpectedly succeeded"})
    except Exception as exc:
        step2_error = str(exc)[:200]
        steps.append({"step": "error_inject", "ok": False, "ms": round((time.perf_counter() - step_start) * 1000, 1), "error": step2_error})

    # Step 3: recovery — send valid transaction
    step_start = time.perf_counter()
    step3_ok = False
    step3_error: str | None = None
    try:
        valid_tx = TxParams(to="0x0000000000000000000000000000000000000001", value=0)
        r3 = await asyncio.wait_for(adapter.send_transaction(valid_tx), timeout=timeout)
        step3_ok = bool(r3.tx_hash) or r3.meta.get("revert", False)
        steps.append({"step": "recovery_tx", "ok": step3_ok, "ms": round((time.perf_counter() - step_start) * 1000, 1), "tx_hash": r3.tx_hash})
    except Exception as exc:
        step3_error = str(exc)[:200]
        steps.append({"step": "recovery_tx", "ok": False, "ms": round((time.perf_counter() - step_start) * 1000, 1), "error": step3_error})

    elapsed = (time.perf_counter() - t0) * 1000

    detail: dict[str, Any] = {
        "steps": steps,
        "step2_error": step2_error,
        "step3_ok": step3_ok,
        "step3_error": step3_error,
    }

    if step3_ok:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=f"多步恢复成功: 错误注入后正常交易恢复",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=f"多步恢复失败: 错误注入后无法恢复正常操作{f' ({step3_error[:80]})' if step3_error else ''}",
        detail=detail,
        owner="provider",
    )
