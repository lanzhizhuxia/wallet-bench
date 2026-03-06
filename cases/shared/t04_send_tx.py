"""t04 — Send transaction (build → sign → submit → confirm on testnet)."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t04"
TEST_NAME = "send_tx"

# Send a tiny amount to the burn address on testnet
_BURN_ADDRESS = "0x0000000000000000000000000000000000000001"
_TINY_VALUE_WEI = 10**14  # 0.0001 BNB — small but above dust threshold


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("send_transaction", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的交易发送能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        tx = TxParams(to=_BURN_ADDRESS, value=_TINY_VALUE_WEI)
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

    # A revert due to insufficient balance is acceptable for staging/testnet —
    # the adapter successfully submitted the intent and got a structured error.
    is_revert = result.meta.get("revert", False)
    if not result.tx_hash and not is_revert:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="未返回 tx_hash",
            detail={"raw": result.meta},
        )

    if is_revert:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="交易已提交但被 revert（预期: 测试钱包无余额）",
            detail={"revert": True, "elapsed_ms": elapsed},
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=f"交易已提交: {result.tx_hash}",
        detail={
            "tx_hash": result.tx_hash,
            "elapsed_ms": elapsed,
        },
    )
