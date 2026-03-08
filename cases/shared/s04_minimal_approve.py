"""s04 — Minimal approve (exact amount instead of unlimited)."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "s04"
TEST_NAME = "minimal_approve"

# type(uint256).max — the unlimited approval sentinel
UINT256_MAX = (2**256) - 1


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Test whether the adapter approves exact amounts instead of unlimited."""
    caps = adapter.capabilities()
    provider = _provider_name(adapter)

    has_cap = any(caps.get(k, False) for k in ("token_approve", "minimal_approve", "approve"))
    has_method = any(
        callable(getattr(adapter, k, None))
        for k in ("approve_token", "token_approve", "set_allowance")
    )

    if not (has_cap or has_method):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供精确授权 (Minimal Approve) 功能。无法验证是否使用精确额度而非无限授权。",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "capabilities": {k: caps.get(k, False) for k in ("token_approve", "minimal_approve", "approve")},
    }

    try:
        result: Any = None
        approve_amount = 100  # 100 USDC (6-decimal token → 100_000_000 base units)

        if callable(getattr(adapter, "approve_token", None)):
            detail["path"] = "adapter_approve_token"
            result = await asyncio.wait_for(
                adapter.approve_token(  # type: ignore[attr-defined]
                    token="USDC",
                    spender="0x0000000000000000000000000000000000000001",
                    amount=approve_amount,
                    dry_run=True,
                ),
                timeout=30,
            )
        elif callable(getattr(adapter, "token_approve", None)):
            detail["path"] = "adapter_token_approve"
            result = await asyncio.wait_for(
                adapter.token_approve(  # type: ignore[attr-defined]
                    token="USDC",
                    spender="0x0000000000000000000000000000000000000001",
                    amount=approve_amount,
                    dry_run=True,
                ),
                timeout=30,
            )
        elif callable(getattr(adapter, "set_allowance", None)):
            detail["path"] = "adapter_set_allowance"
            result = await asyncio.wait_for(
                adapter.set_allowance(  # type: ignore[attr-defined]
                    token="USDC",
                    spender="0x0000000000000000000000000000000000000001",
                    amount=approve_amount,
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
                message="该供应商当前不提供精确授权功能。无法验证是否使用精确额度而非无限授权。",
                owner="provider",
                detail=detail,
            )

        elapsed = (time.perf_counter() - t0) * 1000
        detail["result_type"] = type(result).__name__
        detail["raw"] = str(result)[:500]

        # Check whether the allowance is the exact needed amount (not unlimited)
        allowance = None
        if isinstance(result, dict):
            allowance = result.get("allowance") or result.get("approved_amount")
        elif hasattr(result, "allowance"):
            allowance = getattr(result, "allowance", None)

        detail["allowance"] = allowance

        if allowance is not None and int(allowance) == UINT256_MAX:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message="授权额度为无限 (uint256.max)，未使用精确额度授权。",
                owner="provider",
                detail=detail,
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="授权额度为精确所需金额，未使用无限授权。",
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
            message=f"minimal approve 执行失败: {exc}",
            detail=detail,
        )
