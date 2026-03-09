from __future__ import annotations

import asyncio
import time
from cases.shared._utils import looks_like_success as _looks_like_success  # ISSUE-028 P2-1

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t18"
TEST_NAME = "perps_trading"

# Defaults — overridable via config["test_params"]["t18"]
_DEFAULT_PLATFORM = "hyperliquid"
_DEFAULT_TIMEOUT = 30


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


def _params(config: dict) -> dict[str, Any]:
    """Extract test parameters from config with sane defaults."""
    overrides = config.get("test_params", {}).get("t18", {})
    return {
        "platform": overrides.get("platform", _DEFAULT_PLATFORM),
        "timeout": overrides.get("timeout", _DEFAULT_TIMEOUT),
    }




async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)
    p = _params(config)
    timeout = p["timeout"]

    # --- capability detection ---
    cap_keys = ("perps", "perps_trading", "futures")
    has_cap = any(caps.get(k, False) for k in cap_keys)
    has_method = any(callable(getattr(adapter, k, None)) for k in cap_keys)
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
        "params": p,
        "capabilities": {k: caps.get(k, False) for k in cap_keys},
    }

    try:
        result: Any = None

        if "minara" in provider and callable(getattr(adapter, "_run_minara", None)):
            detail["path"] = "minara_cli"
            result = await asyncio.wait_for(
                adapter._run_minara(  # type: ignore[attr-defined]
                    "perps",
                    "positions",
                    "--platform", p["platform"],
                    timeout=timeout,
                ),
                timeout=timeout,
            )

        elif callable(getattr(adapter, "perps_trading", None)):
            detail["path"] = "adapter_perps_trading"
            result = await asyncio.wait_for(
                adapter.perps_trading(  # type: ignore[attr-defined]
                    platform=p["platform"], dry_run=True,
                ),
                timeout=timeout,
            )

        elif callable(getattr(adapter, "perps", None)):
            detail["path"] = "adapter_perps"
            result = await asyncio.wait_for(
                adapter.perps(  # type: ignore[attr-defined]
                    platform=p["platform"], dry_run=True,
                ),
                timeout=timeout,
            )

        elif callable(getattr(adapter, "futures", None)):
            detail["path"] = "adapter_futures"
            result = await asyncio.wait_for(
                adapter.futures(  # type: ignore[attr-defined]
                    platform=p["platform"], dry_run=True,
                ),
                timeout=timeout,
            )

        else:
            # Capability declared but no callable implementation found
            status = TestStatus.UNSUPPORTED if not has_cap else TestStatus.FAIL
            msg = (
                "该供应商当前不提供永续合约交易功能。如需 Agent 执行永续合约交易，需评估其他方案。"
                if not has_cap
                else "适配器声明支持 perps/futures 能力，但未找到可调用的实现方法。"
            )
            owner = "provider" if not has_cap else "benchmark"
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=status,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message=msg,
                owner=owner,
                detail=detail,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__
        detail["raw"] = str(result)[:500]

        # --- validate result semantics ---
        if not _looks_like_success(result):
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message="perps trading dry-run 返回结果包含错误信号",
                owner="provider",
                detail=detail,
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="perps trading dry-run 执行成功",
            owner="provider",
            detail=detail,
        )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"perps trading 执行超时 (>{timeout}s)",
            owner="provider",
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
            owner="provider",
            detail=detail,
        )
