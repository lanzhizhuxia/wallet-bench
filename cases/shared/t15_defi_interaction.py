from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t15"
TEST_NAME = "defi_interaction"


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


def _provider_hint(config: dict, provider: str) -> bool:
    keys = [str(k).lower() for k in config.get("providers", {}).keys()]
    return any(k in provider for k in keys)


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    has_cap = any(caps.get(k, False) for k in ("defi_interaction", "stake", "lend", "lp", "deposit"))
    has_method = any(callable(getattr(adapter, k, None)) for k in ("stake", "lend", "deposit", "defi_interaction"))
    has_hint = any(k in provider for k in ("minara", "coinbase")) or _provider_hint(config, provider)

    if not (has_cap or has_method or has_hint):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供 DeFi 交互功能（质押、借贷、存款等）。如需 Agent 参与 DeFi 协议，需评估其他方案。",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "supported_protocol_types": ["stake", "lend", "lp", "deposit"],
        "capabilities": {k: caps.get(k, False) for k in ("defi_interaction", "stake", "lend", "lp", "deposit")},
    }

    try:
        result: Any = None

        if "minara" in provider and callable(getattr(adapter, "_run_minara", None)):
            chain = getattr(adapter, "_chain", "base")
            detail["path"] = "minara_cli"
            detail["chain"] = chain
            last_err: Exception | None = None
            for cmd in (
                ("deposit", "-c", chain, "-t", "USDC", "-a", "0.01", "-y"),
                ("stake", "-c", chain, "-t", "USDC", "-a", "0.01", "-y"),
            ):
                try:
                    detail["attempt_cmd"] = list(cmd)
                    result = await asyncio.wait_for(adapter._run_minara(*cmd, timeout=30), timeout=30)  # type: ignore[attr-defined]
                    break
                except Exception as exc:
                    last_err = exc
            if result is None and last_err is not None:
                raise last_err

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
                    message="该供应商当前不提供 DeFi 交互功能。如需 Agent 参与 DeFi 协议，需评估其他方案。",
                    owner="provider",
                    detail=detail,
                )

            payload = {"asset": "USDC", "amount": "0.01", "dry_run": True}
            last_err = None
            for action in ("morpho_deposit", "aave_supply", "stake"):
                try:
                    detail["action"] = action
                    result = await asyncio.wait_for(asyncio.to_thread(run_action, action, payload), timeout=30)
                    break
                except Exception as exc:
                    last_err = exc
            if result is None and last_err is not None:
                raise last_err

        elif callable(getattr(adapter, "defi_interaction", None)):
            detail["path"] = "adapter_defi_interaction"
            result = await asyncio.wait_for(adapter.defi_interaction(dry_run=True), timeout=30)  # type: ignore[attr-defined]

        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="该供应商当前不提供 DeFi 交互功能。如需 Agent 参与 DeFi 协议，需评估其他方案。",
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
            message="已尝试执行 DeFi interaction",
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
            message=f"DeFi interaction 执行失败: {exc}",
            detail=detail,
        )
