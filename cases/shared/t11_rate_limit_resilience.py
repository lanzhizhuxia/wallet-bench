"""t11 — Rate-limit resilience: rapid burst calls to detect throttling."""

from __future__ import annotations

import asyncio
import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t11"
TEST_NAME = "rate_limit_resilience"

_BURST_SIZE = 5
_MAX_RETRIES = 2


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("create_wallet", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的限流韧性测试前提能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    checks: list[dict] = []

    # Phase 1: burst — fire N create_wallet calls as fast as possible
    burst_results: list[dict] = []
    tasks = [adapter.create_wallet() for _ in range(_BURST_SIZE)]
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)

    successes = 0
    rate_limited = 0
    errors = 0
    for i, outcome in enumerate(outcomes):
        if isinstance(outcome, Exception):
            msg = str(outcome).lower()
            if "rate" in msg or "429" in msg or "throttl" in msg or "too many" in msg:
                rate_limited += 1
                burst_results.append({"call": i, "status": "rate_limited", "msg": str(outcome)[:120]})
            else:
                errors += 1
                burst_results.append({"call": i, "status": "error", "msg": str(outcome)[:120]})
        else:
            successes += 1
            burst_results.append({"call": i, "status": "ok"})

    checks.append({
        "test": "burst",
        "ok": successes > 0,  # at least some should succeed
        "msg": f"{successes} ok, {rate_limited} rate-limited, {errors} errors (burst={_BURST_SIZE})",
    })

    # Phase 2: retry after rate-limit — if we got rate-limited, wait and retry
    if rate_limited > 0:
        await asyncio.sleep(2)  # brief cooldown
        retry_ok = 0
        for attempt in range(_MAX_RETRIES):
            try:
                await adapter.create_wallet()
                retry_ok += 1
                break
            except Exception:
                await asyncio.sleep(1)

        checks.append({
            "test": "retry_after_limit",
            "ok": retry_ok > 0,
            "msg": f"Recovery after rate-limit: {'succeeded' if retry_ok else 'still failing'}",
        })
    else:
        checks.append({
            "test": "retry_after_limit",
            "ok": True,
            "msg": "No rate-limiting detected, retry not needed",
        })

    # Phase 3: sign_message burst (if supported)
    if adapter.capabilities().get("sign_message", False):
        sign_tasks = [adapter.sign_message(f"burst_{i}") for i in range(_BURST_SIZE)]
        sign_outcomes = await asyncio.gather(*sign_tasks, return_exceptions=True)
        sign_ok = sum(1 for o in sign_outcomes if not isinstance(o, Exception))
        sign_limited = sum(1 for o in sign_outcomes if isinstance(o, Exception) and
                          any(k in str(o).lower() for k in ("rate", "429", "throttl", "too many")))
        checks.append({
            "test": "sign_burst",
            "ok": sign_ok > 0,
            "msg": f"sign_message burst: {sign_ok} ok, {sign_limited} rate-limited",
        })

    elapsed = (time.perf_counter() - t0) * 1000
    all_ok = all(c["ok"] for c in checks)

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if all_ok else TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=f"限流恢复: {'所有检查通过' if all_ok else '部分检查失败'}",
        detail={"checks": checks, "burst_size": _BURST_SIZE},
    )
