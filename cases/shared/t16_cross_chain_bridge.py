from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t16"
TEST_NAME = "cross_chain_bridge"


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    has_cap = any(caps.get(k, False) for k in ("bridge", "cross_chain_bridge"))
    has_method = any(callable(getattr(adapter, k, None)) for k in ("bridge", "cross_chain_bridge"))
    has_hint = "moonpay" in provider

    if not (has_cap or has_method or has_hint):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供跨链桥接功能。如需 Agent 执行跨链资产转移，需评估其他方案。",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "supported_chain_pairs": ["ethereum->base", "base->arbitrum"],
        "capabilities": {k: caps.get(k, False) for k in ("bridge", "cross_chain_bridge")},
    }

    try:
        result: Any = None

        if "moonpay" in provider and callable(getattr(adapter, "_run_mp", None)):
            wallet = getattr(adapter, "_current_wallet", "bench")
            detail["path"] = "moonpay_cli"
            detail["wallet"] = wallet
            result = await asyncio.wait_for(
                adapter._run_mp(  # type: ignore[attr-defined]
                    "token", "bridge",
                    "--wallet", wallet,
                    "--from-chain", "ethereum",
                    "--to-chain", "base",
                    "--token", "USDC",
                    "--amount", "0.01",
                    "--dry-run",
                    timeout=30,
                ),
                timeout=30,
            )

        elif callable(getattr(adapter, "cross_chain_bridge", None)):
            detail["path"] = "adapter_cross_chain_bridge"
            result = await asyncio.wait_for(
                adapter.cross_chain_bridge(  # type: ignore[attr-defined]
                    from_chain="ethereum",
                    to_chain="base",
                    token="USDC",
                    amount="0.01",
                    dry_run=True,
                ),
                timeout=30,
            )

        elif callable(getattr(adapter, "bridge", None)):
            detail["path"] = "adapter_bridge"
            result = await asyncio.wait_for(
                adapter.bridge(  # type: ignore[attr-defined]
                    from_chain="ethereum",
                    to_chain="base",
                    token="USDC",
                    amount="0.01",
                    dry_run=True,
                ),
                timeout=30,
            )

        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="该供应商当前不提供跨链桥接功能。如需 Agent 执行跨链资产转移，需评估其他方案。",
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
            message="已尝试执行 cross-chain bridge",
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
            message=f"bridge 执行失败: {exc}",
            detail=detail,
        )
