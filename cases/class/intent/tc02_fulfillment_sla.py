"""tc02 (intent) — Fulfillment SLA: measure async operation latency."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "tc02"
TEST_NAME = "fulfillment_sla"

_SLA_SIGN_MS = 30_000  # 30s max for a sign operation


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("sign_message", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的履约 SLA 能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        result = await adapter.sign_message("SLA test message")
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=str(exc),
        )
    elapsed = (time.perf_counter() - t0) * 1000

    if not result.signature:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="未返回签名",
        )

    within_sla = elapsed <= _SLA_SIGN_MS

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if within_sla else TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=f"签名完成，耗时 {elapsed:.0f}ms（SLA: {_SLA_SIGN_MS}ms）",
        detail={
            "elapsed_ms": elapsed,
            "sla_ms": _SLA_SIGN_MS,
            "within_sla": within_sla,
        },
    )
