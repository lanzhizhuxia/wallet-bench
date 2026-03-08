from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "s02"
TEST_NAME = "slippage_guard"

_DEFAULT_TIMEOUT = 30
_EXTREME_SLIPPAGE = 99  # percent — should be rejected or auto-adjusted


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    # --- capability detection ---
    cap_keys = ("slippage_guard", "slippage_protection", "swap")
    has_cap = any(caps.get(k, False) for k in cap_keys)
    method_names = ("set_slippage", "swap", "token_swap")
    has_method = any(callable(getattr(adapter, k, None)) for k in method_names)

    if not (has_cap or has_method):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="Provider does not support slippage guard or swap functionality. Agent cannot verify excessive-slippage protection.",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "extreme_slippage_pct": _EXTREME_SLIPPAGE,
        "capabilities": {k: caps.get(k, False) for k in cap_keys},
    }

    try:
        result: Any = None
        rejected = False

        # Path 1: explicit set_slippage method
        set_slip_fn = getattr(adapter, "set_slippage", None)
        if callable(set_slip_fn):
            detail["path"] = "adapter_set_slippage"
            try:
                result = await asyncio.wait_for(
                    set_slip_fn(_EXTREME_SLIPPAGE),  # type: ignore[operator]
                    timeout=_DEFAULT_TIMEOUT,
                )
                # If set_slippage returns without error, check if it was rejected/adjusted
                if isinstance(result, dict):
                    rejected = bool(
                        result.get("rejected")
                        or result.get("error")
                        or result.get("adjusted")
                        or result.get("clamped")
                    )
                elif isinstance(result, str):
                    raw = result.lower()
                    rejected = any(sig in raw for sig in ("reject", "denied", "adjusted", "clamped", "exceeded", "too high"))
                elif hasattr(result, "rejected"):
                    rejected = bool(getattr(result, "rejected", False))
            except Exception as slip_exc:
                # Rejection via exception is a valid protection mechanism
                detail["set_slippage_error"] = str(slip_exc)[:300]
                rejected = True

        # Path 2: try swap with extreme slippage parameter
        if not rejected:
            for swap_method in ("swap", "token_swap"):
                fn = getattr(adapter, swap_method, None)
                if callable(fn):
                    detail["path"] = f"adapter_{swap_method}_with_slippage"
                    try:
                        result = await asyncio.wait_for(
                            fn(  # type: ignore[operator]
                                "USDC",
                                "USDT",
                                "1.0",
                                slippage=_EXTREME_SLIPPAGE,
                                dry_run=True,
                            ),
                            timeout=_DEFAULT_TIMEOUT,
                        )
                        # Check if result indicates rejection or auto-adjustment
                        if isinstance(result, dict):
                            rejected = bool(
                                result.get("rejected")
                                or result.get("error")
                                or result.get("slippage_adjusted")
                                or result.get("clamped")
                            )
                        elif isinstance(result, str):
                            raw = result.lower()
                            rejected = any(sig in raw for sig in ("reject", "denied", "adjusted", "clamped", "exceeded", "too high"))
                        elif hasattr(result, "rejected"):
                            rejected = bool(getattr(result, "rejected", False))
                    except Exception as swap_exc:
                        detail["swap_error"] = str(swap_exc)[:300]
                        rejected = True
                    break

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__ if result is not None else "None"
        detail["raw"] = str(result)[:500] if result is not None else "None"
        detail["rejected"] = rejected

        if rejected:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=elapsed,
                message=f"Slippage guard active: extreme slippage ({_EXTREME_SLIPPAGE}%) was rejected or auto-adjusted.",
                owner="provider",
                detail=detail,
            )
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message=f"Slippage guard missing: extreme slippage ({_EXTREME_SLIPPAGE}%) was accepted without rejection or adjustment.",
                owner="provider",
                detail=detail,
            )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Slippage guard test timed out (>{_DEFAULT_TIMEOUT}s).",
            owner="provider",
            detail=detail,
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        detail["error"] = str(exc)[:500]
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"Slippage guard test failed: {exc}",
            owner="provider",
            detail=detail,
        )
