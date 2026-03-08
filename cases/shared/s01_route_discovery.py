from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "s01"
TEST_NAME = "route_discovery"

_DEFAULT_TIMEOUT = 30


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    # --- capability detection ---
    cap_keys = ("route_discovery", "swap_routes", "find_routes")
    has_cap = any(caps.get(k, False) for k in cap_keys)
    method_names = ("get_routes", "find_routes", "route_discovery", "swap_routes")
    has_method = any(callable(getattr(adapter, k, None)) for k in method_names)

    if not (has_cap or has_method):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="Provider does not support multi-protocol route discovery. Agent cannot automatically compare swap paths across DEXes.",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "tokens": ["USDC", "USDT"],
        "capabilities": {k: caps.get(k, False) for k in cap_keys},
    }

    try:
        result: Any = None

        for method_name in method_names:
            fn = getattr(adapter, method_name, None)
            if callable(fn):
                detail["path"] = f"adapter_{method_name}"
                result = await asyncio.wait_for(
                    fn(  # type: ignore[operator]
                        token_in="USDC",
                        token_out="USDT",
                        amount="1.0",
                    ),
                    timeout=_DEFAULT_TIMEOUT,
                )
                break

        if result is None:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="Adapter declares route discovery capability but no callable method was found.",
                owner="provider",
                detail=detail,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__
        detail["raw"] = str(result)[:500]

        # --- validate: need >= 2 routes + optimal selection ---
        routes = []
        has_optimal = False

        if isinstance(result, dict):
            routes = result.get("routes", result.get("paths", []))
            has_optimal = bool(result.get("optimal") or result.get("best_route") or result.get("recommended"))
        elif isinstance(result, (list, tuple)):
            routes = result
            has_optimal = len(routes) >= 1  # first route treated as optimal
        elif hasattr(result, "routes"):
            routes = getattr(result, "routes", [])
            has_optimal = bool(getattr(result, "optimal", None) or getattr(result, "best_route", None))

        detail["route_count"] = len(routes)
        detail["has_optimal"] = has_optimal

        if len(routes) >= 2 and has_optimal:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=elapsed,
                message=f"Route discovery returned {len(routes)} routes with optimal selection.",
                owner="provider",
                detail=detail,
            )
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message=f"Route discovery returned {len(routes)} route(s), need >= 2 with optimal selection.",
                owner="provider",
                detail=detail,
            )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Route discovery timed out (>{_DEFAULT_TIMEOUT}s).",
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
            message=f"Route discovery failed: {exc}",
            owner="provider",
            detail=detail,
        )
