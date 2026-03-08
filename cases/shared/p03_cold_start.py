"""p03 — Cold start: initialization to first operation latency."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "p03"
TEST_NAME = "cold_start"

_TOTAL_THRESHOLD_MS = 3000  # 3 seconds


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("create_wallet", False):
        if "create_wallet" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持 create_wallet，无法测量冷启动时延。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的 create_wallet 能力，无法验证。",
            owner="benchmark",
        )

    # Phase 1: setup()
    t_setup_start = time.perf_counter()
    try:
        await adapter.setup()
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t_setup_start) * 1000,
            message=f"setup() 失败: {str(exc)[:200]}",
            owner="provider",
        )
    setup_ms = (time.perf_counter() - t_setup_start) * 1000

    # Phase 2: create_wallet()
    t_create_start = time.perf_counter()
    try:
        wallet = await adapter.create_wallet()
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t_setup_start) * 1000,
            message=f"create_wallet() 失败: {str(exc)[:200]}",
            detail={"setup_ms": round(setup_ms, 1)},
            owner="provider",
        )
    create_wallet_ms = (time.perf_counter() - t_create_start) * 1000

    # Phase 3: first operation — sign_message()
    sign_fn = getattr(adapter, "sign_message", None)
    if sign_fn is None:
        # Fallback: if sign_message not available, measure up to create_wallet only
        total_ms = setup_ms + create_wallet_ms
        detail = {
            "setup_ms": round(setup_ms, 1),
            "create_wallet_ms": round(create_wallet_ms, 1),
            "first_op_ms": 0.0,
            "total_ms": round(total_ms, 1),
            "note": "sign_message not available; total covers setup + create_wallet only",
        }
        status = TestStatus.PASS if total_ms <= _TOTAL_THRESHOLD_MS else TestStatus.FAIL
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=status,
            elapsed_ms=total_ms,
            message=f"冷启动 {total_ms:.0f}ms (setup={setup_ms:.0f}ms, create={create_wallet_ms:.0f}ms, 无 sign_message)",
            detail=detail,
            owner="provider",
        )

    t_sign_start = time.perf_counter()
    try:
        await sign_fn("cold-start-test")
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t_setup_start) * 1000,
            message=f"sign_message() 失败: {str(exc)[:200]}",
            detail={
                "setup_ms": round(setup_ms, 1),
                "create_wallet_ms": round(create_wallet_ms, 1),
            },
            owner="provider",
        )
    first_op_ms = (time.perf_counter() - t_sign_start) * 1000

    total_ms = setup_ms + create_wallet_ms + first_op_ms
    detail = {
        "setup_ms": round(setup_ms, 1),
        "create_wallet_ms": round(create_wallet_ms, 1),
        "first_op_ms": round(first_op_ms, 1),
        "total_ms": round(total_ms, 1),
    }

    if total_ms > _TOTAL_THRESHOLD_MS:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=total_ms,
            message=f"冷启动 {total_ms:.0f}ms 超过阈值 {_TOTAL_THRESHOLD_MS}ms (setup={setup_ms:.0f}ms, create={create_wallet_ms:.0f}ms, sign={first_op_ms:.0f}ms)",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=total_ms,
        message=f"冷启动 {total_ms:.0f}ms (setup={setup_ms:.0f}ms, create={create_wallet_ms:.0f}ms, sign={first_op_ms:.0f}ms)",
        detail=detail,
        owner="provider",
    )
