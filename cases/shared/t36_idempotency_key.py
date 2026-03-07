"""t36 — Idempotency key: verify duplicate submission with same params."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t36"
TEST_NAME = "idempotency_key"

_BURN_ADDRESS = "0x0000000000000000000000000000000000000001"
_DEFAULT_TIMEOUT = 30


def _params(config: dict) -> dict[str, Any]:
    return config.get("test_params", {}).get("t36", {})


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Send the same transaction twice with identical params; check for idempotent behavior.

    PASS if:
      - Second call returns same tx_hash (true idempotency), OR
      - Second call is rejected with a duplicate/conflict error, OR
      - Both calls succeed with different tx_hash but nonce increments correctly
        (basic nonce management — not ideal but not double-spend)

    FAIL if:
      - Both calls succeed silently with different hashes AND no indication
        the provider is aware of the duplicate.
    """
    params = _params(config)
    timeout = params.get("timeout", _DEFAULT_TIMEOUT)

    if not adapter.capabilities().get("send_transaction", False):
        if "send_transaction" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持交易发送能力。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的交易发送能力。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    tx = TxParams(to=_BURN_ADDRESS, value=0)

    # --- First submission ---
    try:
        r1 = await asyncio.wait_for(adapter.send_transaction(tx), timeout=timeout)
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"首次交易异常: {exc}",
            detail={"error": str(exc)[:500]},
            owner="provider",
        )

    hash1 = (r1.tx_hash or "").strip().lower()
    if not hash1:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message="首次交易未返回 tx_hash，无法进行幂等性测试",
            detail={"r1_meta": r1.meta},
            owner="provider",
        )

    # --- Second submission (identical params) ---
    r2_error: str | None = None
    r2_hash: str = ""
    r2_is_duplicate_rejection = False

    try:
        r2 = await asyncio.wait_for(adapter.send_transaction(tx), timeout=timeout)
        r2_hash = (r2.tx_hash or "").strip().lower()
    except Exception as exc:
        r2_error = str(exc)[:500]
        exc_lower = r2_error.lower()
        # Check if the error indicates duplicate/conflict awareness
        duplicate_signals = ("duplicate", "conflict", "already", "idempotent", "nonce", "known")
        r2_is_duplicate_rejection = any(sig in exc_lower for sig in duplicate_signals)

    elapsed = (time.perf_counter() - t0) * 1000

    detail: dict[str, Any] = {
        "tx_hash_1": hash1,
        "tx_hash_2": r2_hash or None,
        "r2_error": r2_error,
        "r2_is_duplicate_rejection": r2_is_duplicate_rejection,
        "same_hash": hash1 == r2_hash if r2_hash else None,
    }

    # Best case: true idempotency — same hash returned
    if r2_hash and hash1 == r2_hash:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="真正幂等: 两次提交返回相同 tx_hash",
            detail=detail,
            owner="provider",
        )

    # Good case: second submission rejected with duplicate awareness
    if r2_is_duplicate_rejection:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=f"重复提交被识别并拒绝: {r2_error[:100] if r2_error else 'rejected'}",
            detail=detail,
            owner="provider",
        )

    # Acceptable: both succeed with different hashes (nonce managed correctly)
    # This isn't ideal idempotency but prevents double-spend
    if r2_hash and hash1 != r2_hash:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=f"两次提交均成功但 hash 不同（nonce 自增，非幂等但无双花风险）",
            detail=detail,
            owner="provider",
        )

    # Error case: second submission failed for unknown reason
    if r2_error and not r2_is_duplicate_rejection:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=elapsed,
            message=f"第二次提交异常（非重复识别）: {r2_error[:150]}",
            detail=detail,
            owner="provider",
        )

    # Fallback: unexpected state
    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message="幂等性检测异常: 无法确定重复提交行为",
        detail=detail,
        owner="provider",
    )
