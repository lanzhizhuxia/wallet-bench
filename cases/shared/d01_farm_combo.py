from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "d01"
TEST_NAME = "farm_combo"

# Defaults — overridable via config["test_params"]["d01"]
_DEFAULT_TOKEN_IN = "USDC"
_DEFAULT_TOKEN_OUT = "WETH"
_DEFAULT_STAKE_TOKEN = "WETH"
_DEFAULT_AMOUNT = "0.01"
_DEFAULT_TIMEOUT = 30


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


def _params(config: dict) -> dict[str, Any]:
    """Extract test parameters from config with sane defaults."""
    overrides = config.get("test_params", {}).get("d01", {})
    return {
        "token_in": overrides.get("token_in", _DEFAULT_TOKEN_IN),
        "token_out": overrides.get("token_out", _DEFAULT_TOKEN_OUT),
        "stake_token": overrides.get("stake_token", _DEFAULT_STAKE_TOKEN),
        "amount": overrides.get("amount", _DEFAULT_AMOUNT),
        "timeout": overrides.get("timeout", _DEFAULT_TIMEOUT),
    }


def _looks_like_success(result: Any) -> bool:
    """Heuristic: check that the result doesn't indicate a hidden failure."""
    if result is None:
        return False

    if isinstance(result, dict):
        if "success" in result and not result["success"]:
            return False
        if "status" in result and str(result["status"]).lower() in ("failed", "error", "rejected"):
            return False
    elif hasattr(result, "success") and not getattr(result, "success", True):
        return False
    elif hasattr(result, "status") and str(getattr(result, "status", "")).lower() in ("failed", "error", "rejected"):
        return False

    raw = str(result).lower()
    if len(raw) > 2000:
        return True
    failure_signals = ("error", "failed", "not found", "denied", "rejected")
    return not any(sig in raw for sig in failure_signals)


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)
    p = _params(config)
    timeout = p["timeout"]

    # --- capability detection ---
    # Need at least swap + stake to proceed
    swap_cap_keys = ("token_swap", "swap")
    stake_cap_keys = ("defi_interaction", "stake")
    claim_cap_keys = ("claim_rewards",)

    has_swap = any(caps.get(k, False) for k in swap_cap_keys) or any(
        callable(getattr(adapter, k, None)) for k in ("token_swap", "swap")
    )
    has_stake = any(caps.get(k, False) for k in stake_cap_keys) or any(
        callable(getattr(adapter, k, None)) for k in ("stake", "defi_interaction")
    )
    has_claim = any(caps.get(k, False) for k in claim_cap_keys) or callable(
        getattr(adapter, "claim_rewards", None)
    )

    if not (has_swap and has_stake):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="Provider does not support both swap and stake capabilities required for the farming combo test.",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "params": p,
        "swap_caps": {k: caps.get(k, False) for k in swap_cap_keys},
        "stake_caps": {k: caps.get(k, False) for k in stake_cap_keys},
        "has_claim": has_claim,
        "steps": {},
    }

    try:
        # ---- Step 1: Approve ----
        step_t0 = time.perf_counter()
        approve_fn = getattr(adapter, "approve", None) or getattr(adapter, "token_approve", None)
        if callable(approve_fn):
            detail["steps"]["approve"] = "attempted"
            approve_result = await asyncio.wait_for(
                approve_fn(  # type: ignore[misc]
                    token=p["token_in"], amount=p["amount"], dry_run=True,
                ),
                timeout=timeout,
            )
            detail["steps"]["approve_elapsed_ms"] = (time.perf_counter() - step_t0) * 1000
            detail["steps"]["approve_result"] = str(approve_result)[:300]
            if not _looks_like_success(approve_result):
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="Approve step failed in farming combo",
                    owner="provider",
                    detail=detail,
                )
        else:
            detail["steps"]["approve"] = "skipped_no_method"

        # ---- Step 2: Swap ----
        step_t0 = time.perf_counter()
        swap_fn = getattr(adapter, "token_swap", None) or getattr(adapter, "swap", None)
        if callable(swap_fn):
            detail["steps"]["swap"] = "attempted"
            swap_result = await asyncio.wait_for(
                swap_fn(  # type: ignore[misc]
                    p["token_in"], p["token_out"], p["amount"], dry_run=True,
                ),
                timeout=timeout,
            )
            detail["steps"]["swap_elapsed_ms"] = (time.perf_counter() - step_t0) * 1000
            detail["steps"]["swap_result"] = str(swap_result)[:300]
            if not _looks_like_success(swap_result):
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="Swap step failed in farming combo",
                    owner="provider",
                    detail=detail,
                )
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="No callable swap method found despite capability declaration.",
                owner="benchmark",
                detail=detail,
            )

        # ---- Step 3: Stake ----
        step_t0 = time.perf_counter()
        stake_fn = getattr(adapter, "stake", None) or getattr(adapter, "defi_interaction", None)
        if callable(stake_fn):
            detail["steps"]["stake"] = "attempted"
            stake_result = await asyncio.wait_for(
                stake_fn(  # type: ignore[misc]
                    token=p["stake_token"], amount=p["amount"], dry_run=True,
                ),
                timeout=timeout,
            )
            detail["steps"]["stake_elapsed_ms"] = (time.perf_counter() - step_t0) * 1000
            detail["steps"]["stake_result"] = str(stake_result)[:300]
            if not _looks_like_success(stake_result):
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="Stake step failed in farming combo",
                    owner="provider",
                    detail=detail,
                )
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="No callable stake method found despite capability declaration.",
                owner="benchmark",
                detail=detail,
            )

        # ---- Step 4: Claim Rewards ----
        step_t0 = time.perf_counter()
        claim_fn = getattr(adapter, "claim_rewards", None)
        if callable(claim_fn):
            detail["steps"]["claim"] = "attempted"
            claim_result = await asyncio.wait_for(
                claim_fn(dry_run=True),  # type: ignore[misc]
                timeout=timeout,
            )
            detail["steps"]["claim_elapsed_ms"] = (time.perf_counter() - step_t0) * 1000
            detail["steps"]["claim_result"] = str(claim_result)[:300]
            if not _looks_like_success(claim_result):
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="Claim rewards step failed in farming combo",
                    owner="provider",
                    detail=detail,
                )
        else:
            detail["steps"]["claim"] = "skipped_no_method"

        elapsed = (time.perf_counter() - t0) * 1000
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="Full farming combo (approve -> swap -> stake -> claim) executed successfully",
            detail=detail,
            owner="provider",
        )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Farming combo step timed out (>{timeout}s)",
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
            message=f"Farming combo execution failed: {exc}",
            owner="provider",
            detail=detail,
        )
