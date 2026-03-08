"""p02 — Burst throughput: sustained sign_message ops in a 30-second window."""

from __future__ import annotations

import asyncio
import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "p02"
TEST_NAME = "burst_throughput"

_WINDOW_SECONDS = 30
_TOTAL_CAP_SECONDS = 35
_OP_TIMEOUT = 30
_THROUGHPUT_THRESHOLD = 1.0  # ops/s — lenient for slower providers


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("sign_message", False):
        if "sign_message" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持 sign_message，无法测量突发吞吐量。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的 sign_message 能力，无法验证。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    completed_ops = 0
    errors: list[str] = []

    while True:
        elapsed_so_far = time.perf_counter() - t0
        if elapsed_so_far >= _WINDOW_SECONDS:
            break
        if elapsed_so_far >= _TOTAL_CAP_SECONDS:
            break

        try:
            await asyncio.wait_for(
                adapter.sign_message(f"bench-burst-{completed_ops}"),
                timeout=_OP_TIMEOUT,
            )
            completed_ops += 1
        except asyncio.TimeoutError:
            errors.append(f"op {completed_ops}: timeout >{_OP_TIMEOUT}s")
            break  # single timeout likely means provider is stuck
        except Exception as exc:
            errors.append(f"op {completed_ops}: {str(exc)[:120]}")
            # continue trying — transient errors should not stop the burst

    elapsed = time.perf_counter() - t0
    elapsed_ms = elapsed * 1000

    if elapsed <= 0 or completed_ops == 0:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed_ms,
            message=f"突发吞吐量测试未完成任何操作: {'; '.join(errors[:3])}",
            detail={"total_ops": 0, "elapsed_seconds": round(elapsed, 2), "errors": errors[:5]},
            owner="provider",
        )

    throughput = completed_ops / elapsed

    detail = {
        "total_ops": completed_ops,
        "elapsed_seconds": round(elapsed, 2),
        "throughput_ops_per_sec": round(throughput, 3),
    }
    if errors:
        detail["errors"] = errors[:5]

    if throughput < _THROUGHPUT_THRESHOLD:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed_ms,
            message=f"吞吐量 {throughput:.2f} ops/s 低于阈值 {_THROUGHPUT_THRESHOLD} ops/s ({completed_ops} ops / {elapsed:.1f}s)",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed_ms,
        message=f"吞吐量 {throughput:.2f} ops/s ({completed_ops} ops / {elapsed:.1f}s)",
        detail=detail,
        owner="provider",
    )
