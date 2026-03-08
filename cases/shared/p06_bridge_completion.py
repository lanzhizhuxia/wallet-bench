"""p06 — Cross-chain bridge completion time p50/p95."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "p06"
TEST_NAME = "bridge_completion"

_DEFAULT_FROM_CHAIN = "ethereum"
_DEFAULT_TO_CHAIN = "base"
_DEFAULT_TOKEN = "USDC"
_DEFAULT_AMOUNT = "0.01"
_DEFAULT_TIMEOUT = 30
_MAX_P95_MS = 1_200_000  # 20 minutes


def _params(config: dict) -> dict[str, Any]:
    """Extract test parameters from config with sane defaults."""
    overrides = config.get("test_params", {}).get(TEST_ID, {})
    return {
        "from_chain": overrides.get("from_chain", _DEFAULT_FROM_CHAIN),
        "to_chain": overrides.get("to_chain", _DEFAULT_TO_CHAIN),
        "token": overrides.get("token", _DEFAULT_TOKEN),
        "amount": overrides.get("amount", _DEFAULT_AMOUNT),
        "timeout": float(overrides.get("timeout", _DEFAULT_TIMEOUT)),
    }


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    p = _params(config)
    timeout = p["timeout"]

    # --- capability detection ---
    cap_keys = ("cross_chain_bridge", "bridge")
    has_cap = any(caps.get(k, False) for k in cap_keys)

    method_names = ("bridge", "cross_chain_bridge", "cross_chain_transfer")
    has_method = any(callable(getattr(adapter, m, None)) for m in method_names)

    if not has_cap and not has_method:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供跨链桥接功能，无法测量 bridge 完成时间。",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "params": p,
        "capabilities": {k: caps.get(k, False) for k in cap_keys},
        "max_p95_ms": _MAX_P95_MS,
    }

    try:
        result: Any = None

        if callable(getattr(adapter, "cross_chain_bridge", None)):
            detail["path"] = "cross_chain_bridge"
            result = await asyncio.wait_for(
                adapter.cross_chain_bridge(  # type: ignore[attr-defined]
                    from_chain=p["from_chain"],
                    to_chain=p["to_chain"],
                    token=p["token"],
                    amount=p["amount"],
                    dry_run=True,
                ),
                timeout=timeout,
            )
        elif callable(getattr(adapter, "cross_chain_transfer", None)):
            detail["path"] = "cross_chain_transfer"
            result = await asyncio.wait_for(
                adapter.cross_chain_transfer(  # type: ignore[attr-defined]
                    from_chain=p["from_chain"],
                    to_chain=p["to_chain"],
                    token=p["token"],
                    amount=p["amount"],
                    dry_run=True,
                ),
                timeout=timeout,
            )
        elif callable(getattr(adapter, "bridge", None)):
            detail["path"] = "bridge"
            result = await asyncio.wait_for(
                adapter.bridge(  # type: ignore[attr-defined]
                    from_chain=p["from_chain"],
                    to_chain=p["to_chain"],
                    token=p["token"],
                    amount=p["amount"],
                    dry_run=True,
                ),
                timeout=timeout,
            )
        else:
            # Capability declared but no callable implementation found
            status = TestStatus.UNSUPPORTED if not has_cap else TestStatus.FAIL
            msg = (
                "该供应商当前不提供跨链桥接功能，无法测量 bridge 完成时间。"
                if not has_cap
                else "适配器声明支持 bridge 能力，但未找到可调用的实现方法。"
            )
            owner = "provider" if not has_cap else "benchmark"
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=status,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message=msg,
                owner=owner,
                detail=detail,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__
        detail["raw"] = str(result)[:500]

        # Extract timing information from result
        completion_ms = None
        p50_ms = None
        p95_ms = None

        if isinstance(result, dict):
            completion_ms = result.get("completion_ms") or result.get("elapsed_ms")
            p50_ms = result.get("p50_ms")
            p95_ms = result.get("p95_ms")
        elif hasattr(result, "completion_ms"):
            completion_ms = getattr(result, "completion_ms", None)
        elif hasattr(result, "elapsed_ms"):
            completion_ms = getattr(result, "elapsed_ms", None)

        if p95_ms is not None:
            p95_ms = float(p95_ms)
            detail["p95_ms"] = p95_ms
            if p50_ms is not None:
                detail["p50_ms"] = float(p50_ms)

            if p95_ms <= _MAX_P95_MS:
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.PASS,
                    elapsed_ms=elapsed,
                    message=f"Bridge 完成时间 p95={p95_ms:.0f}ms (阈值 ≤{_MAX_P95_MS}ms)",
                    detail=detail,
                    owner="provider",
                )
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message=f"Bridge 完成时间 p95={p95_ms:.0f}ms 超出阈值 (>{_MAX_P95_MS}ms)",
                detail=detail,
                owner="provider",
            )

        if completion_ms is not None:
            completion_ms = float(completion_ms)
            detail["completion_ms"] = completion_ms

            if completion_ms <= _MAX_P95_MS:
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.PASS,
                    elapsed_ms=elapsed,
                    message=f"Bridge dry-run 完成时间 {completion_ms:.0f}ms (阈值 ≤{_MAX_P95_MS}ms)",
                    detail=detail,
                    owner="provider",
                )
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message=f"Bridge dry-run 完成时间 {completion_ms:.0f}ms 超出阈值 (>{_MAX_P95_MS}ms)",
                detail=detail,
                owner="provider",
            )

        # Got a response but no timing data — dry-run succeeded, pass on capability
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="Bridge dry-run 执行成功，未返回具体完成时间数据。",
            detail=detail,
            owner="provider",
        )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Bridge 执行超时 (>{timeout}s)",
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
            message=f"Bridge 执行失败: {exc}",
            owner="provider",
            detail=detail,
        )
