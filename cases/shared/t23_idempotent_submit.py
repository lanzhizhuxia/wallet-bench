"""t23 — Idempotent submit behavior for duplicate transaction params."""
from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t23"
TEST_NAME = "idempotent_submit"

_TO = "0x0000000000000000000000000000000000000001"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    # 能力检查：不支持交易提交则跳过
    if not adapter.capabilities().get("send_transaction", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的幂等提交能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    tx = TxParams(to=_TO, value=0)

    try:
        first = await adapter.send_transaction(tx)
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"首次提交异常: {exc}",
        )

    try:
        second = await adapter.send_transaction(tx)
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="重复提交被优雅拒绝，未出现双花",
            detail={"first_tx_hash": (first.tx_hash or "").strip(), "second_error": str(exc)},
        )

    elapsed = (time.perf_counter() - t0) * 1000
    h1 = (first.tx_hash or "").strip()
    h2 = (second.tx_hash or "").strip()

    # 判定：相同 hash 或第二次失败都可接受；两次成功且 hash 不同视为风险
    if h1 and h2 and h1 != h2:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="重复提交产生两笔不同成功交易，存在非幂等风险",
            detail={"first_tx_hash": h1, "second_tx_hash": h2, "first_meta": first.meta, "second_meta": second.meta},
        )

    if h1 and h2 and h1 == h2:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="重复提交返回同一 tx_hash，幂等性良好",
            detail={"tx_hash": h1},
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message="重复提交结果不明确",
        detail={"first_tx_hash": h1, "second_tx_hash": h2, "first_meta": first.meta, "second_meta": second.meta},
    )
