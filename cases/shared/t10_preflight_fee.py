"""t10 — Preflight fee estimation."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t10"
TEST_NAME = "preflight_fee"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("estimate_gas", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的 Gas 费用预估能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        tx = TxParams(
            to="0x0000000000000000000000000000000000000001",
            value=0,  # zero value to avoid insufficient-funds errors on unfunded wallets
        )
        # Use the adapter's estimate_gas if available
        if hasattr(adapter, "estimate_gas"):
            result = await adapter.estimate_gas(tx)
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.INCONCLUSIVE,
                message="基准侧已标记支持 Gas 费用预估，但本轮验证链路尚未打通，结果待确认。",
                owner="benchmark",
            )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=str(exc),
        )
    elapsed = (time.perf_counter() - t0) * 1000

    # Basic sanity: we got some response
    if not result:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="Gas 预估结果为空",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message="Gas 预估返回成功",
        detail={"estimation": result},
    )
