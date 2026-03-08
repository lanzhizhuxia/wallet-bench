"""s06 — Unsafe approve detection (identify and block suspicious permit/approve requests)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "s06"
TEST_NAME = "unsafe_approve_detect"

# Known phishing-pattern spender address (fake contract, not a real protocol)
PHISHING_SPENDER = "0xdEaD000000000000000000000000000000000000"
# type(uint256).max — unlimited approval commonly used in phishing
UINT256_MAX = (2**256) - 1


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Test whether the adapter can identify and block suspicious permit/approve requests."""
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    has_cap = any(caps.get(k, False) for k in ("unsafe_approve_detect", "approve_guard", "security_scan"))
    has_method = any(
        callable(getattr(adapter, k, None))
        for k in ("detect_unsafe_approve", "scan_approval", "check_permit")
    )

    if not (has_cap or has_method):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供恶意授权检测 (Unsafe Approve Detect) 功能。无法验证是否能识别和拦截可疑的 permit/approve 请求。",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "capabilities": {k: caps.get(k, False) for k in ("unsafe_approve_detect", "approve_guard", "security_scan")},
        "phishing_spender": PHISHING_SPENDER,
        "approve_amount": str(UINT256_MAX),
    }

    try:
        result: Any = None

        if callable(getattr(adapter, "detect_unsafe_approve", None)):
            detail["path"] = "adapter_detect_unsafe_approve"
            result = await asyncio.wait_for(
                adapter.detect_unsafe_approve(  # type: ignore[attr-defined]
                    token="USDC",
                    spender=PHISHING_SPENDER,
                    amount=UINT256_MAX,
                ),
                timeout=30,
            )
        elif callable(getattr(adapter, "scan_approval", None)):
            detail["path"] = "adapter_scan_approval"
            result = await asyncio.wait_for(
                adapter.scan_approval(  # type: ignore[attr-defined]
                    token="USDC",
                    spender=PHISHING_SPENDER,
                    amount=UINT256_MAX,
                ),
                timeout=30,
            )
        elif callable(getattr(adapter, "check_permit", None)):
            detail["path"] = "adapter_check_permit"
            result = await asyncio.wait_for(
                adapter.check_permit(  # type: ignore[attr-defined]
                    token="USDC",
                    spender=PHISHING_SPENDER,
                    amount=UINT256_MAX,
                ),
                timeout=30,
            )
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="该供应商当前不提供恶意授权检测功能。无法验证是否能识别和拦截可疑的 approve 请求。",
                owner="provider",
                detail=detail,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__
        detail["raw"] = str(result)[:500]

        # Determine whether the suspicious approve was detected and rejected
        detected = False
        if isinstance(result, dict):
            detected = bool(
                result.get("blocked")
                or result.get("rejected")
                or result.get("unsafe")
                or result.get("is_phishing")
            )
        elif isinstance(result, bool):
            detected = result
        elif hasattr(result, "blocked"):
            detected = bool(getattr(result, "blocked", False))
        elif hasattr(result, "unsafe"):
            detected = bool(getattr(result, "unsafe", False))

        detail["detected"] = detected

        if not detected:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message="未能识别或拦截可疑的无限授权请求（疑似钓鱼地址 + uint256.max 额度）。",
                owner="provider",
                detail=detail,
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="已成功识别并拦截可疑的 approve 请求。",
            detail=detail,
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        detail["error"] = str(exc)[:500]

        # Some adapters may raise an exception to reject the unsafe approve — that counts as detection
        err_lower = str(exc).lower()
        if any(keyword in err_lower for keyword in ("blocked", "rejected", "unsafe", "phishing", "suspicious", "denied")):
            detail["detected_via_exception"] = True
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=elapsed,
                message=f"通过异常拦截了可疑的 approve 请求: {exc}",
                detail=detail,
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"unsafe approve detect 执行失败: {exc}",
            detail=detail,
        )
