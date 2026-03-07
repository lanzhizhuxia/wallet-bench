"""a04 — Token cost: measure API call count and resource consumption per task."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "a04"
TEST_NAME = "token_cost"

_DEFAULT_TIMEOUT = 30


def _params(config: dict) -> dict[str, Any]:
    return config.get("test_params", {}).get("a04", {})


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Measure the cost of completing a standard task: create wallet + sign + send.

    Reports total elapsed time, number of API calls, and average latency per call.
    This helps Agent builders estimate budget impact.
    """
    params = _params(config)
    timeout = params.get("timeout", _DEFAULT_TIMEOUT)

    t0 = time.perf_counter()
    calls: list[dict[str, Any]] = []
    caps = adapter.capabilities()

    # Step 1: create_wallet
    step_start = time.perf_counter()
    try:
        wallet = await asyncio.wait_for(adapter.create_wallet(), timeout=timeout)
        calls.append({
            "op": "create_wallet",
            "ms": round((time.perf_counter() - step_start) * 1000, 1),
            "ok": True,
        })
    except Exception as exc:
        calls.append({
            "op": "create_wallet",
            "ms": round((time.perf_counter() - step_start) * 1000, 1),
            "ok": False,
            "error": str(exc)[:100],
        })
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"create_wallet 失败，无法完成成本评估: {exc}",
            detail={"calls": calls},
            owner="provider",
        )

    # Step 2: sign_message (if supported)
    if caps.get("sign_message", False):
        step_start = time.perf_counter()
        try:
            await asyncio.wait_for(adapter.sign_message("cost-probe"), timeout=timeout)
            calls.append({
                "op": "sign_message",
                "ms": round((time.perf_counter() - step_start) * 1000, 1),
                "ok": True,
            })
        except Exception as exc:
            calls.append({
                "op": "sign_message",
                "ms": round((time.perf_counter() - step_start) * 1000, 1),
                "ok": False,
                "error": str(exc)[:100],
            })

    # Step 3: send_transaction (if supported)
    if caps.get("send_transaction", False):
        step_start = time.perf_counter()
        try:
            tx = TxParams(to="0x0000000000000000000000000000000000000001", value=0)
            await asyncio.wait_for(adapter.send_transaction(tx), timeout=timeout)
            calls.append({
                "op": "send_transaction",
                "ms": round((time.perf_counter() - step_start) * 1000, 1),
                "ok": True,
            })
        except Exception as exc:
            calls.append({
                "op": "send_transaction",
                "ms": round((time.perf_counter() - step_start) * 1000, 1),
                "ok": False,
                "error": str(exc)[:100],
            })

    elapsed = (time.perf_counter() - t0) * 1000
    total_calls = len(calls)
    successful = sum(1 for c in calls if c["ok"])
    total_api_ms = sum(c["ms"] for c in calls)
    avg_ms = total_api_ms / total_calls if total_calls > 0 else 0

    detail: dict[str, Any] = {
        "total_calls": total_calls,
        "successful_calls": successful,
        "total_api_ms": round(total_api_ms, 1),
        "avg_ms_per_call": round(avg_ms, 1),
        "calls": calls,
    }

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=f"标准任务完成: {successful}/{total_calls} 调用成功, 总耗时 {total_api_ms:.0f}ms, 平均 {avg_ms:.0f}ms/调用",
        detail=detail,
        owner="benchmark",
    )
