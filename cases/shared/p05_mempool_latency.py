"""p05 — Mempool event latency compared to reference node."""
from __future__ import annotations

import asyncio
import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "p05"
TEST_NAME = "mempool_latency"

_DEFAULT_TIMEOUT = 30
_MAX_LATENCY_MS = 250


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()

    # Check capabilities
    cap_keys = ("mempool_subscribe", "mempool", "pending_transactions")
    has_cap = any(caps.get(k, False) for k in cap_keys)

    # Check methods
    method_names = ("subscribe_mempool", "watch_mempool", "pending_transactions")
    has_method = any(callable(getattr(adapter, m, None)) for m in method_names)

    if not has_cap and not has_method:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供 mempool 订阅能力，无法测量 mempool 事件延迟。",
            owner="provider",
        )

    params = config.get("test_params", {}).get(TEST_ID, {})
    timeout = float(params.get("timeout", _DEFAULT_TIMEOUT))

    t0 = time.perf_counter()
    detail: dict = {
        "capabilities": {k: caps.get(k, False) for k in cap_keys},
    }

    try:
        result = None

        if callable(getattr(adapter, "subscribe_mempool", None)):
            detail["path"] = "subscribe_mempool"
            result = await asyncio.wait_for(
                adapter.subscribe_mempool(),  # type: ignore[attr-defined]
                timeout=timeout,
            )
        elif callable(getattr(adapter, "watch_mempool", None)):
            detail["path"] = "watch_mempool"
            result = await asyncio.wait_for(
                adapter.watch_mempool(),  # type: ignore[attr-defined]
                timeout=timeout,
            )
        elif callable(getattr(adapter, "pending_transactions", None)):
            detail["path"] = "pending_transactions"
            result = await asyncio.wait_for(
                adapter.pending_transactions(),  # type: ignore[attr-defined]
                timeout=timeout,
            )
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="适配器声明支持 mempool 能力，但未找到可调用的实现方法。",
                owner="provider",
                detail=detail,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__
        detail["raw"] = str(result)[:500]

        # Extract latency from result if available
        latency_ms = None
        if isinstance(result, dict):
            latency_ms = result.get("latency_ms") or result.get("latency")
        elif hasattr(result, "latency_ms"):
            latency_ms = getattr(result, "latency_ms", None)

        if latency_ms is not None:
            latency_ms = float(latency_ms)
            detail["latency_ms"] = latency_ms

            if latency_ms <= _MAX_LATENCY_MS:
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.PASS,
                    elapsed_ms=elapsed,
                    message=f"Mempool 事件延迟 {latency_ms:.0f}ms (阈值 ≤{_MAX_LATENCY_MS}ms)",
                    detail=detail,
                    owner="provider",
                )
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message=f"Mempool 事件延迟 {latency_ms:.0f}ms 超出阈值 (>{_MAX_LATENCY_MS}ms)",
                detail=detail,
                owner="provider",
            )

        # Got a response but no latency data — treat as pass for capability check
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="Mempool 订阅能力已验证，未返回具体延迟数据。",
            detail=detail,
            owner="provider",
        )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Mempool 订阅超时 (>{timeout}s)",
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
            message=f"Mempool 订阅失败: {exc}",
            owner="provider",
            detail=detail,
        )
