"""t24 — Retry and backoff behavior around rate limiting."""
from __future__ import annotations

import asyncio
import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t24"
TEST_NAME = "retry_backoff"

_BURST = 10


def _is_rate_limited(exc: Exception) -> bool:
    text = str(exc).lower()
    return "429" in text or "rate" in text or "throttl" in text or "too many" in text


def _retry_hint(exc: Exception) -> str:
    text = str(exc)
    for key in ("retry-after", "retry after", "retry_after", "backoff"):
        if key in text.lower():
            return key
    if exc.args and isinstance(exc.args[0], dict):
        payload = exc.args[0]
        for k in ("retry_after", "retryAfter", "Retry-After"):
            if k in payload:
                return f"{k}={payload[k]}"
    return ""


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("sign_message", False):
        if "sign_message" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持消息签名，无法执行重试退避测试。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的重试退避测试前提能力（需消息签名），无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    checks: list[dict] = []
    rate_limited = 0
    success = 0
    first_limit_hint = ""

    for i in range(_BURST):
        try:
            sig = await adapter.sign_message(f"retry_backoff_{i}")
            if sig.signature:
                success += 1
            else:
                checks.append({"call": i, "status": "empty_signature"})
        except Exception as exc:
            if _is_rate_limited(exc):
                rate_limited += 1
                if not first_limit_hint:
                    first_limit_hint = _retry_hint(exc)
                checks.append({"call": i, "status": "rate_limited", "hint": _retry_hint(exc), "error": str(exc)[:180]})
            else:
                checks.append({"call": i, "status": "error", "error": str(exc)[:180]})

    if rate_limited == 0:
        elapsed = (time.perf_counter() - t0) * 1000
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="未检测到限流，连续调用稳定",
            detail={"burst": _BURST, "success": success, "rate_limited": rate_limited, "checks": checks},
        )

    await asyncio.sleep(2)
    recovered = False
    recovery_error = ""
    try:
        retry_sig = await adapter.sign_message("retry_backoff_recovery")
        recovered = bool(retry_sig.signature)
    except Exception as exc:
        recovery_error = str(exc)

    elapsed = (time.perf_counter() - t0) * 1000
    has_hint = bool(first_limit_hint)
    if recovered and has_hint:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="发生限流但提供恢复信息，且冷却后恢复成功",
            detail={
                "burst": _BURST,
                "success": success,
                "rate_limited": rate_limited,
                "retry_hint": first_limit_hint,
                "checks": checks,
            },
        )

    if recovered and not has_hint:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="发生限流且可恢复，但未给出明确 retry/backoff 信息",
            detail={"rate_limited": rate_limited, "checks": checks},
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message="发生限流后未恢复",
        detail={"rate_limited": rate_limited, "retry_hint": first_limit_hint, "recovery_error": recovery_error, "checks": checks},
    )
