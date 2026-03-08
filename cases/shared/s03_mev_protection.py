from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "s03"
TEST_NAME = "mev_protection"

_DEFAULT_TIMEOUT = 30


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    # --- capability detection ---
    cap_keys = ("mev_protection", "private_relay", "flashbots")
    has_cap = any(caps.get(k, False) for k in cap_keys)
    method_names = ("send_private_transaction", "mev_protect", "private_relay")
    has_method = any(callable(getattr(adapter, k, None)) for k in method_names)

    if not (has_cap or has_method):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="Provider does not support MEV protection / private relay. Agent transactions may be vulnerable to sandwich attacks.",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "capabilities": {k: caps.get(k, False) for k in cap_keys},
    }

    try:
        result: Any = None

        for method_name in method_names:
            fn = getattr(adapter, method_name, None)
            if callable(fn):
                detail["path"] = f"adapter_{method_name}"
                result = await asyncio.wait_for(
                    fn(),  # type: ignore[operator]
                    timeout=_DEFAULT_TIMEOUT,
                )
                break

        if result is None:
            # Capability declared but no callable implementation
            if has_cap:
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="Adapter declares MEV protection capability but no callable method was found.",
                    owner="benchmark",
                    detail=detail,
                )
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="Provider does not support MEV protection / private relay.",
                owner="provider",
                detail=detail,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__
        detail["raw"] = str(result)[:500]

        # --- validate: check if MEV-protected path is available ---
        mev_available = False

        if isinstance(result, dict):
            mev_available = bool(
                result.get("protected")
                or result.get("mev_protected")
                or result.get("private_relay")
                or result.get("flashbots")
                or result.get("success")
                or result.get("available")
            )
        elif isinstance(result, bool):
            mev_available = result
        elif isinstance(result, str):
            raw = result.lower()
            mev_available = any(sig in raw for sig in ("protected", "private", "flashbots", "success", "enabled", "available"))
        elif hasattr(result, "protected"):
            mev_available = bool(getattr(result, "protected", False))
        elif hasattr(result, "success"):
            mev_available = bool(getattr(result, "success", False))
        else:
            # Non-None result from a MEV-protection method is a positive signal
            mev_available = True

        detail["mev_available"] = mev_available

        if mev_available:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=elapsed,
                message="MEV-protected transaction path is available.",
                owner="provider",
                detail=detail,
            )
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message="MEV protection method returned but no protected path was confirmed.",
                owner="provider",
                detail=detail,
            )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"MEV protection test timed out (>{_DEFAULT_TIMEOUT}s).",
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
            message=f"MEV protection test failed: {exc}",
            owner="provider",
            detail=detail,
        )
