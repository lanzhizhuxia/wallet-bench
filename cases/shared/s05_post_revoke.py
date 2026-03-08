"""s05 — Post-revoke (auto-revoke or reduce allowance after operation)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "s05"
TEST_NAME = "post_revoke"


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Test whether the adapter auto-revokes or reduces allowance after operation."""
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    has_cap = any(caps.get(k, False) for k in ("revoke_approval", "post_revoke", "allowance_management"))
    has_method = any(
        callable(getattr(adapter, k, None))
        for k in ("revoke_approval", "reset_allowance", "post_revoke")
    )

    if not (has_cap or has_method):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供操作后自动撤销/归零授权 (Post-Revoke) 功能。无法验证授权是否在操作后被清除。",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "capabilities": {k: caps.get(k, False) for k in ("revoke_approval", "post_revoke", "allowance_management")},
    }

    try:
        result: Any = None

        if callable(getattr(adapter, "revoke_approval", None)):
            detail["path"] = "adapter_revoke_approval"
            result = await asyncio.wait_for(
                adapter.revoke_approval(  # type: ignore[attr-defined]
                    token="USDC",
                    spender="0x0000000000000000000000000000000000000001",
                    dry_run=True,
                ),
                timeout=30,
            )
        elif callable(getattr(adapter, "reset_allowance", None)):
            detail["path"] = "adapter_reset_allowance"
            result = await asyncio.wait_for(
                adapter.reset_allowance(  # type: ignore[attr-defined]
                    token="USDC",
                    spender="0x0000000000000000000000000000000000000001",
                    dry_run=True,
                ),
                timeout=30,
            )
        elif callable(getattr(adapter, "post_revoke", None)):
            detail["path"] = "adapter_post_revoke"
            result = await asyncio.wait_for(
                adapter.post_revoke(  # type: ignore[attr-defined]
                    token="USDC",
                    spender="0x0000000000000000000000000000000000000001",
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
                message="该供应商当前不提供操作后自动撤销授权功能。无法验证授权是否在操作后被清除。",
                owner="provider",
                detail=detail,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__
        detail["raw"] = str(result)[:500]

        # Check whether the allowance was zeroed or reduced after the operation
        remaining_allowance = None
        if isinstance(result, dict):
            remaining_allowance = result.get("remaining_allowance") or result.get("allowance")
        elif hasattr(result, "remaining_allowance"):
            remaining_allowance = getattr(result, "remaining_allowance", None)
        elif hasattr(result, "allowance"):
            remaining_allowance = getattr(result, "allowance", None)

        detail["remaining_allowance"] = remaining_allowance

        if remaining_allowance is not None and int(remaining_allowance) > 0:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message=f"操作后授权未归零，剩余授权额度: {remaining_allowance}。",
                owner="provider",
                detail=detail,
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="操作后授权已被撤销或归零。",
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
            message=f"post revoke 执行失败: {exc}",
            detail=detail,
        )
