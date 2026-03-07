from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t14"
TEST_NAME = "token_swap"


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    has_cap = any(caps.get(k, False) for k in ("token_swap", "swap"))
    has_method = any(callable(getattr(adapter, k, None)) for k in ("token_swap", "swap"))
    has_hint = any(k in provider for k in ("moonpay", "minara", "coinbase", "okx"))

    if not (has_cap or has_method or has_hint):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供代币兑换 (Swap) 功能。如需 Agent 自动执行 Swap 交易，需评估其他方案。",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "tokens": ["USDC", "USDT"],
        "dexes": [],
        "capabilities": {k: caps.get(k, False) for k in ("token_swap", "swap")},
    }

    try:
        result: Any = None

        if "moonpay" in provider and callable(getattr(adapter, "_run_mp", None)):
            wallet = getattr(adapter, "_current_wallet", "bench")
            chain = getattr(adapter, "_chain", "ethereum")
            detail["path"] = "moonpay_cli"
            detail["wallet"] = wallet
            detail["chain"] = chain
            result = await asyncio.wait_for(
                adapter._run_mp(  # type: ignore[attr-defined]
                    "token", "swap",
                    "--wallet", wallet,
                    "--chain", chain,
                    "--token-in", "USDC",
                    "--token-out", "USDT",
                    "--amount", "0.01",
                    "--dry-run",
                    timeout=30,
                ),
                timeout=30,
            )

        elif "minara" in provider and callable(getattr(adapter, "_run_minara", None)):
            chain = getattr(adapter, "_chain", "base")
            detail["path"] = "minara_cli"
            detail["chain"] = chain
            result = await asyncio.wait_for(
                adapter._run_minara(  # type: ignore[attr-defined]
                    "swap",
                    "-c", chain,
                    "-f", "USDC",
                    "-t", "USDT",
                    "-a", "0.01",
                    "-y",
                    timeout=30,
                ),
                timeout=30,
            )

        elif "okx" in provider and callable(getattr(adapter, "token_swap", None)):
            chain = getattr(adapter, "_chain", "ethereum")
            detail["path"] = "okx_onchainos_cli"
            detail["chain"] = chain
            result = await asyncio.wait_for(
                adapter.token_swap(  # type: ignore[attr-defined]
                    "USDC", "USDT", "0.01", dry_run=True,
                ),
                timeout=30,
            )

        elif "coinbase" in provider:
            detail["path"] = "coinbase_sdk"
            wp = getattr(adapter, "_wallet_provider", None)
            if wp is None:
                await adapter.setup()
                wp = getattr(adapter, "_wallet_provider", None)

            run_action = getattr(wp, "run_action", None) or getattr(adapter, "run_action", None)
            if not callable(run_action):
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.UNSUPPORTED,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="该供应商当前不提供代币兑换功能。如需 Agent 自动执行 Swap 交易，需评估其他方案。",
                    owner="provider",
                    detail=detail,
                )

            payload = {
                "amount": "0.01",
                "from_token": "USDC",
                "to_token": "USDT",
                "dry_run": True,
            }
            last_err = None
            for action in ("token_swap", "swap", "trade"):
                try:
                    detail["action"] = action
                    result = await asyncio.wait_for(asyncio.to_thread(run_action, action, payload), timeout=30)
                    break
                except Exception as exc:
                    last_err = exc
            if result is None and last_err is not None:
                raise last_err

        elif callable(getattr(adapter, "token_swap", None)):
            detail["path"] = "adapter_token_swap"
            result = await asyncio.wait_for(
                adapter.token_swap("USDC", "USDT", "0.01", dry_run=True),  # type: ignore[attr-defined]
                timeout=30,
            )

        elif callable(getattr(adapter, "swap", None)):
            detail["path"] = "adapter_swap"
            result = await asyncio.wait_for(
                adapter.swap("USDC", "USDT", "0.01", dry_run=True),  # type: ignore[attr-defined]
                timeout=30,
            )

        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="该供应商当前不提供代币兑换功能。如需 Agent 自动执行 Swap 交易，需评估其他方案。",
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
            message="已尝试执行 token swap",
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
            message=f"token swap 执行失败: {exc}",
            detail=detail,
        )
