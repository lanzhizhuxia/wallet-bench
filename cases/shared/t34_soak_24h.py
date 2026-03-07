"""t34 — Soak stability: sustained operation success rate over N rounds."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t34"
TEST_NAME = "soak_24h"

_DEFAULT_ROUNDS = 20
_DEFAULT_TIMEOUT = 15
_SUCCESS_THRESHOLD = 0.9  # 90% success rate required


def _params(config: dict) -> dict[str, Any]:
    return config.get("test_params", {}).get("t34", {})


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Run mixed operations (create_wallet + sign_message + estimate_gas) for N rounds.

    This is a scaled-down soak test — the full 24h version is configured via
    test_params.t34.rounds (default 20 for CI, set to 1000+ for real soak).
    """
    params = _params(config)
    rounds = params.get("rounds", _DEFAULT_ROUNDS)
    timeout = params.get("timeout", _DEFAULT_TIMEOUT)
    threshold = params.get("success_threshold", _SUCCESS_THRESHOLD)

    caps = adapter.capabilities()

    t0 = time.perf_counter()
    successes = 0
    errors: list[str] = []
    latencies: list[float] = []

    for i in range(rounds):
        op_start = time.perf_counter()
        try:
            # Rotate through operations
            phase = i % 3
            if phase == 0:
                await asyncio.wait_for(adapter.create_wallet(), timeout=timeout)
            elif phase == 1 and caps.get("sign_message", False):
                await asyncio.wait_for(adapter.sign_message(f"soak-{i}"), timeout=timeout)
            elif phase == 2 and caps.get("send_transaction", False):
                tx = TxParams(to="0x0000000000000000000000000000000000000001", value=0)
                await asyncio.wait_for(adapter.send_transaction(tx), timeout=timeout)
            else:
                await asyncio.wait_for(adapter.create_wallet(), timeout=timeout)

            latencies.append((time.perf_counter() - op_start) * 1000)
            successes += 1
        except asyncio.TimeoutError:
            errors.append(f"round {i}: timeout")
        except Exception as exc:
            errors.append(f"round {i}: {str(exc)[:80]}")

    elapsed = (time.perf_counter() - t0) * 1000
    success_rate = successes / rounds if rounds > 0 else 0

    sorted_lat = sorted(latencies) if latencies else []
    p50 = sorted_lat[len(sorted_lat) // 2] if sorted_lat else 0.0
    p95_idx = min(int(len(sorted_lat) * 0.95), len(sorted_lat) - 1) if sorted_lat else 0
    p95 = sorted_lat[p95_idx] if sorted_lat else 0.0

    detail: dict[str, Any] = {
        "rounds": rounds,
        "successes": successes,
        "success_rate": round(success_rate, 3),
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "error_count": len(errors),
        "threshold": threshold,
    }
    if errors:
        detail["sample_errors"] = errors[:5]

    if success_rate < threshold:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"持续运行成功率 {success_rate:.0%} 低于阈值 {threshold:.0%} ({successes}/{rounds}轮, P50={p50:.0f}ms)",
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=f"持续运行 {rounds} 轮, 成功率 {success_rate:.0%}, P50={p50:.0f}ms, P95={p95:.0f}ms",
        detail=detail,
        owner="provider",
    )
