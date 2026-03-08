"""ag03 — Error self-recovery: after a bad request, can the adapter retry with corrected params."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "ag03"
TEST_NAME = "error_self_recovery"

_DEFAULT_TIMEOUT = 30

_INVALID_ADDRESS = "0xinvalid"
_VALID_ADDRESS = "0x0000000000000000000000000000000000000001"


def _has_structured_error(meta: Any) -> bool:
    """Check whether meta contains machine-readable error information."""
    if not isinstance(meta, dict):
        return False
    for key in ("error", "message", "reason", "error_code", "code", "retry", "suggestion"):
        if str(meta.get(key, "")).strip():
            return True
    return False


def _indicates_auto_retry(meta: Any) -> bool:
    """Check whether meta signals that adapter performed an auto-retry."""
    if not isinstance(meta, dict):
        return False
    for key in ("retried", "auto_corrected", "retry_count", "corrected", "recovered"):
        val = meta.get(key)
        if val is not None and val is not False and val != 0:
            return True
    return False


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    unsupported = adapter.provider_unsupported()
    t0 = time.perf_counter()

    detail: dict[str, Any] = {}
    notes: list[str] = []

    # ── Require send_transaction or sign_message ──────────────────────────
    can_send = caps.get("send_transaction", False)
    can_sign = caps.get("sign_message", False)

    if not can_send and not can_sign:
        owner = "provider" if {"send_transaction", "sign_message"}.issubset(unsupported) else "benchmark"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            elapsed_ms=0.0,
            message="Neither send_transaction nor sign_message available; cannot test error recovery.",
            detail={"capabilities": caps},
            owner=owner,
        )

    if not can_send:
        owner = "provider" if "send_transaction" in unsupported else "benchmark"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            elapsed_ms=0.0,
            message="send_transaction not available; error self-recovery test requires it.",
            detail={"capabilities": caps},
            owner=owner,
        )

    # ── Step 1: send deliberately bad request ─────────────────────────────
    bad_tx = TxParams(to=_INVALID_ADDRESS, value=0)
    step1_error: str | None = None
    step1_structured = False
    step1_auto_retry = False
    step1_meta: dict[str, Any] = {}

    try:
        result_bad = await asyncio.wait_for(
            adapter.send_transaction(bad_tx), timeout=_DEFAULT_TIMEOUT
        )
        step1_meta = result_bad.meta if isinstance(result_bad.meta, dict) else {}
        step1_structured = _has_structured_error(step1_meta)
        step1_auto_retry = _indicates_auto_retry(step1_meta)
        # If a tx_hash came back for an invalid address, that's unexpected but record it
        if result_bad.tx_hash:
            notes.append(f"bad request unexpectedly returned tx_hash={result_bad.tx_hash}")
        detail["step1_result"] = {
            "tx_hash": result_bad.tx_hash,
            "status": result_bad.status,
            "meta": result_bad.meta,
        }
    except Exception as exc:
        step1_error = str(exc)[:300]
        step1_structured = bool(step1_error.strip())
        detail["step1_exception"] = step1_error

    detail["step1_structured_error"] = step1_structured
    detail["step1_auto_retry"] = step1_auto_retry

    # ── Step 2: send valid request to verify recovery ─────────────────────
    valid_tx = TxParams(to=_VALID_ADDRESS, value=0)
    step2_ok = False
    step2_error: str | None = None

    try:
        result_good = await asyncio.wait_for(
            adapter.send_transaction(valid_tx), timeout=_DEFAULT_TIMEOUT
        )
        # Consider success if we get a tx_hash or at least no crash
        step2_ok = bool(result_good.tx_hash) or result_good.meta.get("revert", False)
        # Even without tx_hash, if we got a structured response, adapter recovered
        if not step2_ok and isinstance(result_good.meta, dict) and len(result_good.meta) > 0:
            step2_ok = True
            notes.append("step2 returned structured meta without tx_hash — counted as recovery")
        detail["step2_result"] = {
            "tx_hash": result_good.tx_hash,
            "status": result_good.status,
            "meta": result_good.meta,
        }
    except Exception as exc:
        step2_error = str(exc)[:300]
        detail["step2_exception"] = step2_error

    detail["step2_ok"] = step2_ok

    elapsed = (time.perf_counter() - t0) * 1000

    # ── Determine result ──────────────────────────────────────────────────
    # PASS if: adapter auto-retried with corrected params (best case),
    #   OR returned structured error AND successfully handled valid follow-up
    auto_recovered = step1_auto_retry and step2_ok
    structured_and_recovered = step1_structured and step2_ok

    if auto_recovered:
        message = "Auto-correction detected: adapter retried with corrected params and recovered."
        detail["pass_reason"] = "auto_retry"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=message,
            detail=detail,
            owner="industry",
        )

    if structured_and_recovered:
        message = "Structured error on bad request; valid follow-up succeeded — recovery path OK."
        if notes:
            message = f"{message} ({'; '.join(notes)})"
        detail["pass_reason"] = "structured_error_plus_recovery"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=message,
            detail=detail,
            owner="industry",
        )

    # Fail: opaque error or no recovery
    fail_reasons: list[str] = []
    if not step1_structured:
        fail_reasons.append("error from bad request was opaque/empty")
    if not step2_ok:
        fail_reasons.append("valid follow-up after error did not succeed")
    if step2_error:
        fail_reasons.append(f"step2 error: {step2_error[:80]}")

    message = f"Error self-recovery failed: {'; '.join(fail_reasons)}"
    if notes:
        message = f"{message} ({'; '.join(notes)})"

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=message,
        detail=detail,
        owner="provider",
    )
