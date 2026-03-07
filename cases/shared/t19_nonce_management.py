"""t19 — Nonce management under sequential submissions."""
from __future__ import annotations

import asyncio
import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t19"
TEST_NAME = "nonce_management"

_TO = "0x0000000000000000000000000000000000000001"
_VALUE = 0
_DEFAULT_TIMEOUT = 30


def _normalize_hash(h: str | None) -> str:
    """Normalize tx_hash for reliable comparison: strip + lowercase."""
    return (h or "").strip().lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    timeout = config.get("test_params", {}).get("t19", {}).get("timeout", _DEFAULT_TIMEOUT)

    if not adapter.capabilities().get("send_transaction", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的 Nonce 管理能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()

    # --- first transaction ---
    try:
        tx1 = TxParams(to=_TO, value=_VALUE)
        r1 = await asyncio.wait_for(adapter.send_transaction(tx1), timeout=timeout)
    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"首笔交易超时 (>{timeout}s)",
            owner="provider",
        )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"首笔交易异常: {exc}",
            detail={"error": str(exc)[:500]},
            owner="provider",
        )

    # --- second transaction ---
    try:
        tx2 = TxParams(to=_TO, value=_VALUE)
        r2 = await asyncio.wait_for(adapter.send_transaction(tx2), timeout=timeout)
    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"第二笔交易超时 (>{timeout}s)，疑似 nonce 冲突或管理异常",
            detail={"first_tx_hash": _normalize_hash(r1.tx_hash)},
            owner="provider",
        )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message="第二笔交易失败，疑似 nonce 冲突或管理异常",
            detail={"first_tx_hash": _normalize_hash(r1.tx_hash), "error": str(exc)[:500]},
            owner="provider",
        )

    elapsed = (time.perf_counter() - t0) * 1000
    h1 = _normalize_hash(r1.tx_hash)
    h2 = _normalize_hash(r2.tx_hash)

    detail = {
        "tx1_hash": h1,
        "tx2_hash": h2,
        "tx1_status": r1.status,
        "tx2_status": r2.status,
        "tx1_meta": r1.meta,
        "tx2_meta": r2.meta,
    }

    if not h1 or not h2:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="nonce 管理失败: 至少一个交易未返回 tx_hash",
            detail=detail,
            owner="provider",
        )

    if h1 == h2:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="nonce 管理异常: 两笔不同提交返回相同 tx_hash",
            detail=detail,
            owner="provider",
        )

    # Check on-chain success status if available
    status_info = ""
    if r1.status is not None and r1.status != 1:
        status_info += f" tx1 链上状态={r1.status}"
    if r2.status is not None and r2.status != 1:
        status_info += f" tx2 链上状态={r2.status}"

    if status_info:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"交易已提交但链上状态异常:{status_info}",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message="两笔交易均成功，nonce 自动递增正常",
        detail=detail,
        owner="provider",
    )
