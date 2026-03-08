"""p04 — Gas estimation accuracy (absolute error percentage)."""
from __future__ import annotations

import asyncio
import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "p04"
TEST_NAME = "gas_accuracy"

_BURN_ADDRESS = "0x0000000000000000000000000000000000000001"
_DEFAULT_TIMEOUT = 30


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()

    if not caps.get("estimate_gas", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供 Gas 预估能力，无法测量预估精度。",
            owner="provider",
        )

    estimate_fn = getattr(adapter, "estimate_gas", None)
    if not callable(estimate_fn):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="适配器未实现 estimate_gas 方法。",
            owner="provider",
        )

    params = config.get("test_params", {}).get(TEST_ID, {})
    timeout = float(params.get("timeout", _DEFAULT_TIMEOUT))

    tx = TxParams(to=_BURN_ADDRESS, value=0)
    t0 = time.perf_counter()

    # Step 1: estimate gas
    try:
        estimated = await asyncio.wait_for(estimate_fn(tx), timeout=timeout)
    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Gas 预估超时 (>{timeout}s)",
            owner="provider",
        )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Gas 预估失败: {exc}",
            owner="provider",
        )

    # Normalize estimated to int
    if isinstance(estimated, dict):
        estimated = estimated.get("gas") or estimated.get("gasLimit") or estimated.get("gas_limit")
    if estimated is not None:
        estimated = int(estimated)

    if not estimated or estimated <= 0:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message="Gas 预估返回值无效",
            detail={"estimated_raw": estimated},
            owner="provider",
        )

    # Step 2: send transaction and measure actual gas_used
    try:
        tx_result = await asyncio.wait_for(
            adapter.send_transaction(TxParams(to=_BURN_ADDRESS, value=0)),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"交易发送超时 (>{timeout}s)",
            detail={"estimated": estimated},
            owner="provider",
        )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"交易发送失败: {exc}",
            detail={"estimated": estimated},
            owner="provider",
        )

    elapsed = (time.perf_counter() - t0) * 1000

    actual = tx_result.gas_used
    if actual is None or actual <= 0:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=elapsed,
            message="交易结果未返回 gas_used，无法计算预估精度。",
            detail={"estimated": estimated, "tx_hash": tx_result.tx_hash},
            owner="benchmark",
        )

    error_pct = abs(estimated - actual) / actual * 100

    detail = {
        "estimated": estimated,
        "actual": actual,
        "error_pct": round(error_pct, 2),
        "tx_hash": tx_result.tx_hash,
    }

    if error_pct <= 15:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=f"Gas 预估误差 {error_pct:.1f}% (阈值 ≤15%)",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=f"Gas 预估误差 {error_pct:.1f}% 超出阈值 (>15%)",
        detail=detail,
        owner="provider",
    )
