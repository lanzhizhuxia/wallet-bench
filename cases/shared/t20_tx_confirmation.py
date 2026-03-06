"""t20 — Transaction confirmation surface quality."""
from __future__ import annotations

import re
import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t20"
TEST_NAME = "tx_confirmation"

_TO = "0x0000000000000000000000000000000000000001"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("send_transaction", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的交易确认追踪能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        tx = TxParams(to=_TO, value=0)
        result = await adapter.send_transaction(tx)
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=str(exc),
        )

    elapsed = (time.perf_counter() - t0) * 1000
    tx_hash = (result.tx_hash or "").strip()
    valid_hex = bool(re.fullmatch(r"0x[0-9a-fA-F]+", tx_hash))

    if not tx_hash or not valid_hex:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="tx_confirmation 失败: tx_hash 缺失或格式无效",
            detail={"tx_hash": tx_hash, "meta": result.meta},
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message="tx_hash 返回有效",
        detail={
            "tx_hash": tx_hash,
            "block_number": result.block_number,
            "gas_used": result.gas_used,
            "meta": result.meta,
        },
    )
