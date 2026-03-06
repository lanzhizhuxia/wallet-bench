from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t18"
TEST_NAME = "perps_trading"


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    has_cap = any(caps.get(k, False) for k in ("perps", "perps_trading", "futures"))
    has_method = any(callable(getattr(adapter, k, None)) for k in ("perps", "perps_trading", "futures"))
    has_hint = "minara" in provider

    if not (has_cap or has_method or has_hint):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供永续合约交易功能。如需 Agent 执行永续合约交易，需评估其他方案。",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "supported_platforms": ["hyperliquid"],
        "capabilities": {k: caps.get(k, False) for k in ("perps", "perps_trading", "futures")},
    }

    try:
        result: Any = None

        if "minara" in provider and callable(getattr(adapter, "_run_minara", None)):
            detail["path"] = "minara_cli"
            result = await asyncio.wait_for(
                adapter._run_minara(  # type: ignore[attr-defined]
                    "perps",
                    "positions",
                    "--platform", "hyperliquid",
                    timeout=30,
                ),
                timeout=30,
            )

        elif callable(getattr(adapter, "perps_trading", None)):
            detail["path"] = "adapter_perps_trading"
            result = await asyncio.wait_for(
                adapter.perps_trading(platform="hyperliquid", dry_run=True),  # type: ignore[attr-defined]
                timeout=30,
            )

        elif callable(getattr(adapter, "perps", None)):
            detail["path"] = "adapter_perps"
            result = await asyncio.wait_for(
                adapter.perps(platform="hyperliquid", dry_run=True),  # type: ignore[attr-defined]
                timeout=30,
            )

        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="该供应商当前不提供永续合约交易功能。如需 Agent 执行永续合约交易，需评估其他方案。",
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
            message="已尝试执行 perps trading",
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
            message=f"perps trading 执行失败: {exc}",
            detail=detail,
        )
