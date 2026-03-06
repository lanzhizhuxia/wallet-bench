"""t19 — Nonce management under sequential submissions."""
from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t19"
TEST_NAME = "nonce_management"

_TO = "0x0000000000000000000000000000000000000001"
_VALUE = 0


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("send_transaction", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的 Nonce 管理能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        tx1 = TxParams(to=_TO, value=_VALUE)
        r1 = await adapter.send_transaction(tx1)
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"首笔交易异常: {exc}",
        )

    try:
        tx2 = TxParams(to=_TO, value=_VALUE)
        r2 = await adapter.send_transaction(tx2)
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message="第二笔交易失败，疑似 nonce 冲突或管理异常",
            detail={"first_tx_hash": (r1.tx_hash or "").strip(), "error": str(exc)},
        )

    elapsed = (time.perf_counter() - t0) * 1000
    h1 = (r1.tx_hash or "").strip()
    h2 = (r2.tx_hash or "").strip()

    if not h1 or not h2:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="nonce 管理失败: 至少一个交易未返回 tx_hash",
            detail={"tx1_hash": h1, "tx2_hash": h2, "tx1_meta": r1.meta, "tx2_meta": r2.meta},
        )

    if h1 == h2:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="nonce 管理异常: 两笔不同提交返回相同 tx_hash",
            detail={"tx1_hash": h1, "tx2_hash": h2},
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message="两笔交易均成功，nonce 自动递增正常",
        detail={"tx1_hash": h1, "tx2_hash": h2},
    )
