from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t17"
TEST_NAME = "prediction_market"


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    has_cap = any(caps.get(k, False) for k in ("prediction_market", "market_prediction"))
    has_method = any(callable(getattr(adapter, k, None)) for k in ("prediction_market", "market_prediction"))
    has_hint = "moonpay" in provider

    if not (has_cap or has_method or has_hint):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供预测市场交易功能。如需 Agent 参与预测市场，需评估其他方案。",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "supported_platforms": ["polymarket"],
        "capabilities": {k: caps.get(k, False) for k in ("prediction_market", "market_prediction")},
    }

    try:
        result: Any = None

        if "moonpay" in provider and callable(getattr(adapter, "_run_mp", None)):
            wallet = getattr(adapter, "_current_wallet", "bench")
            detail["path"] = "moonpay_cli"
            detail["wallet"] = wallet
            result = await asyncio.wait_for(
                adapter._run_mp(  # type: ignore[attr-defined]
                    "prediction-market", "markets",
                    "--wallet", wallet,
                    "--platform", "polymarket",
                    timeout=30,
                ),
                timeout=30,
            )

        elif callable(getattr(adapter, "prediction_market", None)):
            detail["path"] = "adapter_prediction_market"
            result = await asyncio.wait_for(
                adapter.prediction_market(platform="polymarket", dry_run=True),  # type: ignore[attr-defined]
                timeout=30,
            )

        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="该供应商当前不提供预测市场交易功能。如需 Agent 参与预测市场，需评估其他方案。",
                owner="provider",
                detail=detail,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__
        detail["raw"] = str(result)[:500]
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="已尝试执行 prediction market 操作",
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
            message=f"prediction market 执行失败: {exc}",
            detail=detail,
        )
