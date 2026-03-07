"""t20 — Transaction confirmation surface quality."""
from __future__ import annotations

import asyncio
import re
import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t20"
TEST_NAME = "tx_confirmation"

_TO = "0x0000000000000000000000000000000000000001"
_DEFAULT_TIMEOUT = 30

# Standard Ethereum tx_hash: 0x + 64 hex chars (32 bytes)
_TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    timeout = config.get("test_params", {}).get("t20", {}).get("timeout", _DEFAULT_TIMEOUT)

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
        result = await asyncio.wait_for(adapter.send_transaction(tx), timeout=timeout)
    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"send_transaction 超时 (>{timeout}s)",
            detail={"to": _TO, "value": 0},
            owner="provider",
        )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"send_transaction 异常: {exc}",
            detail={"to": _TO, "value": 0, "error": str(exc)[:500]},
            owner="provider",
        )

    elapsed = (time.perf_counter() - t0) * 1000
    tx_hash = (result.tx_hash or "").strip()
    valid_hex = bool(_TX_HASH_RE.fullmatch(tx_hash))

    detail = {
        "tx_hash": tx_hash,
        "block_number": result.block_number,
        "gas_used": result.gas_used,
        "status": result.status,
        "meta": result.meta,
    }

    if not tx_hash:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="tx_confirmation 失败: tx_hash 缺失",
            detail=detail,
            owner="provider",
        )

    if not valid_hex:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"tx_confirmation 失败: tx_hash 格式无效 (期望 0x + 64位hex, 实际长度={len(tx_hash)})",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message="tx_hash 返回有效 (0x + 64位hex)",
        detail=detail,
        owner="provider",
    )
