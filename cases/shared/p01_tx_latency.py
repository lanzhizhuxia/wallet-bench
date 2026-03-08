"""p01 — Transaction submission latency (p50 / p95 / p99)."""

from __future__ import annotations

import asyncio
import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "p01"
TEST_NAME = "tx_latency"

_BURN_ADDRESS = "0x0000000000000000000000000000000000000001"
_ITERATIONS = 5
_TIMEOUT = 30
_P95_THRESHOLD_MS = 1200  # 1.2 seconds


def _percentile(sorted_values: list[float], p: float) -> float:
    """Return the p-th percentile (0-100) from a sorted list."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * p / 100.0
    f = int(k)
    c = f + 1
    if c >= len(sorted_values):
        return sorted_values[-1]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("send_transaction", False):
        if "send_transaction" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持 send_transaction，无法测量交易提交时延。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的 send_transaction 能力，无法验证。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    latencies: list[float] = []
    errors: list[str] = []
    tx = TxParams(to=_BURN_ADDRESS, value=0)

    for i in range(_ITERATIONS):
        op_start = time.perf_counter()
        try:
            await asyncio.wait_for(
                adapter.send_transaction(tx),
                timeout=_TIMEOUT,
            )
            latencies.append((time.perf_counter() - op_start) * 1000)
        except asyncio.TimeoutError:
            errors.append(f"iteration {i}: timeout >{_TIMEOUT}s")
        except Exception as exc:
            errors.append(f"iteration {i}: {str(exc)[:120]}")

    elapsed = (time.perf_counter() - t0) * 1000

    if not latencies:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"所有 {_ITERATIONS} 次迭代均失败: {'; '.join(errors[:3])}",
            detail={"errors": errors, "iterations": _ITERATIONS},
            owner="provider",
        )

    sorted_lat = sorted(latencies)
    p50 = _percentile(sorted_lat, 50)
    p95 = _percentile(sorted_lat, 95)
    p99 = _percentile(sorted_lat, 99)

    detail = {
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "p99_ms": round(p99, 1),
        "latencies_ms": [round(l, 1) for l in latencies],
        "iterations": _ITERATIONS,
        "successes": len(latencies),
    }
    if errors:
        detail["errors"] = errors[:5]

    if p95 > _P95_THRESHOLD_MS:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"P95 时延 {p95:.0f}ms 超过阈值 {_P95_THRESHOLD_MS}ms (P50={p50:.0f}ms, P99={p99:.0f}ms)",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=f"P50={p50:.0f}ms, P95={p95:.0f}ms, P99={p99:.0f}ms ({len(latencies)}/{_ITERATIONS}次成功)",
        detail=detail,
        owner="provider",
    )
