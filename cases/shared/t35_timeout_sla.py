"""t35 — Response latency SLA: measure P50/P95 for key operations."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t35"
TEST_NAME = "timeout_sla"

_DEFAULT_TIMEOUT = 15
_DEFAULT_ROUNDS = 5
_P95_THRESHOLD_MS = 10_000  # 10 seconds — above this is FAIL


def _params(config: dict) -> dict[str, Any]:
    return config.get("test_params", {}).get("t35", {})


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
    params = _params(config)
    timeout = params.get("timeout", _DEFAULT_TIMEOUT)
    rounds = params.get("rounds", _DEFAULT_ROUNDS)
    p95_threshold = params.get("p95_threshold_ms", _P95_THRESHOLD_MS)

    if not adapter.capabilities().get("sign_message", False):
        if "sign_message" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持 sign_message，无法测量响应时延。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的 sign_message 能力。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    latencies: list[float] = []
    errors: list[str] = []

    for i in range(rounds):
        op_start = time.perf_counter()
        try:
            await asyncio.wait_for(
                adapter.sign_message(f"sla-probe-{i}"),
                timeout=timeout,
            )
            latencies.append((time.perf_counter() - op_start) * 1000)
        except asyncio.TimeoutError:
            errors.append(f"round {i}: timeout >{timeout}s")
        except Exception as exc:
            errors.append(f"round {i}: {str(exc)[:120]}")

    elapsed = (time.perf_counter() - t0) * 1000

    if not latencies:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"所有 {rounds} 轮均失败: {'; '.join(errors[:3])}",
            detail={"errors": errors, "rounds": rounds},
            owner="provider",
        )

    sorted_lat = sorted(latencies)
    p50 = _percentile(sorted_lat, 50)
    p95 = _percentile(sorted_lat, 95)
    success_rate = len(latencies) / rounds

    detail: dict[str, Any] = {
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "min_ms": round(sorted_lat[0], 1),
        "max_ms": round(sorted_lat[-1], 1),
        "success_rate": round(success_rate, 2),
        "rounds": rounds,
        "successes": len(latencies),
    }
    if errors:
        detail["errors"] = errors[:5]

    if p95 > p95_threshold:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"P95 时延 {p95:.0f}ms 超过阈值 {p95_threshold}ms (P50={p50:.0f}ms, 成功率={success_rate:.0%})",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=f"P50={p50:.0f}ms, P95={p95:.0f}ms, 成功率={success_rate:.0%} ({len(latencies)}/{rounds}轮)",
        detail=detail,
        owner="provider",
    )
