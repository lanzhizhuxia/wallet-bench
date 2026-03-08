from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t16"
TEST_NAME = "cross_chain_bridge"

# Defaults — overridable via config["test_params"]["t16"]
_DEFAULT_FROM_CHAIN = "ethereum"
_DEFAULT_TO_CHAIN = "base"
_DEFAULT_TOKEN = "USDC"
_DEFAULT_AMOUNT = "0.01"
_DEFAULT_TIMEOUT = 30


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


def _params(config: dict) -> dict[str, Any]:
    """Extract test parameters from config with sane defaults."""
    overrides = config.get("test_params", {}).get("t16", {})
    return {
        "from_chain": overrides.get("from_chain", _DEFAULT_FROM_CHAIN),
        "to_chain": overrides.get("to_chain", _DEFAULT_TO_CHAIN),
        "token": overrides.get("token", _DEFAULT_TOKEN),
        "amount": overrides.get("amount", _DEFAULT_AMOUNT),
        "timeout": overrides.get("timeout", _DEFAULT_TIMEOUT),
    }


def _looks_like_success(result: Any) -> bool:
    """Heuristic: check that the result doesn't indicate a hidden failure.

    Handles both string responses and dict/object results with explicit
    success/status fields.
    """
    if result is None:
        return False

    # Structured result with explicit success/status field
    if isinstance(result, dict):
        if "success" in result and not result["success"]:
            return False
        if "status" in result and str(result["status"]).lower() in ("failed", "error", "rejected"):
            return False
    elif hasattr(result, "success") and not getattr(result, "success", True):
        return False
    elif hasattr(result, "status") and str(getattr(result, "status", "")).lower() in ("failed", "error", "rejected"):
        return False

    # Keyword blacklist on stringified result (narrower scope: only check short reprs)
    raw = str(result).lower()
    if len(raw) > 2000:
        failure_signals = ("error", "failed", "not found", "denied", "rejected", "exception", "traceback")
        failure_count = sum(1 for s in failure_signals if s in raw[:500])
        if failure_count >= 2:
            return False
        return True
    failure_signals = ("error", "failed", "not found", "denied", "rejected")
    return not any(sig in raw for sig in failure_signals)


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)
    p = _params(config)
    timeout = p["timeout"]

    # --- capability detection ---
    cap_keys = ("bridge", "cross_chain_bridge")
    has_cap = any(caps.get(k, False) for k in cap_keys)
    has_method = any(callable(getattr(adapter, k, None)) for k in cap_keys)
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
        "params": p,
        "capabilities": {k: caps.get(k, False) for k in cap_keys},
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
                    "--from-chain", p["from_chain"],
                    "--to-chain", p["to_chain"],
                    "--token", p["token"],
                    "--amount", p["amount"],
                    "--dry-run",
                    timeout=timeout,
                ),
                timeout=timeout,
            )

        elif callable(getattr(adapter, "cross_chain_bridge", None)):
            detail["path"] = "adapter_cross_chain_bridge"
            result = await asyncio.wait_for(
                adapter.cross_chain_bridge(  # type: ignore[attr-defined]
                    from_chain=p["from_chain"],
                    to_chain=p["to_chain"],
                    token=p["token"],
                    amount=p["amount"],
                    dry_run=True,
                ),
                timeout=timeout,
            )

        elif callable(getattr(adapter, "bridge", None)):
            detail["path"] = "adapter_bridge"
            result = await asyncio.wait_for(
                adapter.bridge(  # type: ignore[attr-defined]
                    from_chain=p["from_chain"],
                    to_chain=p["to_chain"],
                    token=p["token"],
                    amount=p["amount"],
                    dry_run=True,
                ),
                timeout=timeout,
            )

        else:
            # Capability declared but no callable implementation found
            status = TestStatus.UNSUPPORTED if not has_cap else TestStatus.FAIL
            msg = (
                "该供应商当前不提供跨链桥接功能。如需 Agent 执行跨链资产转移，需评估其他方案。"
                if not has_cap
                else "适配器声明支持 bridge 能力，但未找到可调用的实现方法。"
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
                message="bridge dry-run 返回结果包含错误信号",
                owner="provider",
                detail=detail,
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="cross-chain bridge dry-run 执行成功",
            owner="provider",
            detail=detail,
        )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"bridge 执行超时 (>{timeout}s)",
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
            message=f"bridge 执行失败: {exc}",
            owner="provider",
            detail=detail,
        )
