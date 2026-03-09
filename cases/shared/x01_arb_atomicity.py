from __future__ import annotations

import asyncio
import time
from cases.shared._utils import looks_like_success as _looks_like_success  # ISSUE-028 P2-1

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "x01"
TEST_NAME = "arb_atomicity"

# Defaults — overridable via config["test_params"]["x01"]
_DEFAULT_CHAIN_A = "ethereum"
_DEFAULT_CHAIN_B = "base"
_DEFAULT_TOKEN_A = "USDC"
_DEFAULT_TOKEN_B = "WETH"
_DEFAULT_AMOUNT = "0.01"
_DEFAULT_TIMEOUT = 30


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


def _params(config: dict) -> dict[str, Any]:
    """Extract test parameters from config with sane defaults."""
    overrides = config.get("test_params", {}).get("x01", {})
    return {
        "chain_a": overrides.get("chain_a", _DEFAULT_CHAIN_A),
        "chain_b": overrides.get("chain_b", _DEFAULT_CHAIN_B),
        "token_a": overrides.get("token_a", _DEFAULT_TOKEN_A),
        "token_b": overrides.get("token_b", _DEFAULT_TOKEN_B),
        "amount": overrides.get("amount", _DEFAULT_AMOUNT),
        "timeout": overrides.get("timeout", _DEFAULT_TIMEOUT),
    }




def _looks_like_rollback(result: Any) -> bool:
    """Heuristic: check whether a failed leg result indicates safe rollback."""
    if result is None:
        return False

    if isinstance(result, dict):
        if result.get("rolled_back", False):
            return True
        if result.get("funds_safe", False):
            return True
        status = str(result.get("status", "")).lower()
        if status in ("rolled_back", "reverted", "refunded"):
            return True

    raw = str(result).lower()
    rollback_signals = ("rolled back", "reverted", "refunded", "funds safe", "no funds locked")
    return any(sig in raw for sig in rollback_signals)


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    provider = _provider_name(adapter)
    p = _params(config)
    timeout = p["timeout"]

    # --- capability detection ---
    bridge_cap_keys = ("cross_chain_bridge", "bridge")
    swap_cap_keys = ("swap", "token_swap")

    has_bridge = any(caps.get(k, False) for k in bridge_cap_keys) or any(
        callable(getattr(adapter, k, None)) for k in bridge_cap_keys
    )
    has_swap = any(caps.get(k, False) for k in swap_cap_keys) or any(
        callable(getattr(adapter, k, None)) for k in ("token_swap", "swap")
    )

    if not has_bridge:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="Provider does not support bridge capability required for cross-chain arbitrage atomicity test.",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "params": p,
        "bridge_caps": {k: caps.get(k, False) for k in bridge_cap_keys},
        "swap_caps": {k: caps.get(k, False) for k in swap_cap_keys},
        "legs": {},
    }

    try:
        # ---- Leg 1: Swap on chain A ----
        leg1_t0 = time.perf_counter()
        swap_fn = getattr(adapter, "token_swap", None) or getattr(adapter, "swap", None)
        if callable(swap_fn):
            detail["legs"]["leg1_swap"] = "attempted"
            leg1_result = await asyncio.wait_for(
                swap_fn(  # type: ignore[misc]
                    p["token_a"], p["token_b"], p["amount"], dry_run=True,
                ),
                timeout=timeout,
            )
            detail["legs"]["leg1_elapsed_ms"] = (time.perf_counter() - leg1_t0) * 1000
            detail["legs"]["leg1_result"] = str(leg1_result)[:300]
            leg1_ok = _looks_like_success(leg1_result)
            detail["legs"]["leg1_success"] = leg1_ok
        else:
            detail["legs"]["leg1_swap"] = "skipped_no_method"
            leg1_ok = True  # proceed to bridge test even without swap

        # ---- Leg 2: Bridge from chain A to chain B ----
        leg2_t0 = time.perf_counter()
        bridge_fn = getattr(adapter, "cross_chain_bridge", None) or getattr(adapter, "bridge", None)
        if callable(bridge_fn):
            detail["legs"]["leg2_bridge"] = "attempted"
            leg2_result = await asyncio.wait_for(
                bridge_fn(  # type: ignore[misc]
                    from_chain=p["chain_a"],
                    to_chain=p["chain_b"],
                    token=p["token_b"],
                    amount=p["amount"],
                    dry_run=True,
                ),
                timeout=timeout,
            )
            detail["legs"]["leg2_elapsed_ms"] = (time.perf_counter() - leg2_t0) * 1000
            detail["legs"]["leg2_result"] = str(leg2_result)[:300]
            leg2_ok = _looks_like_success(leg2_result)
            detail["legs"]["leg2_success"] = leg2_ok
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="No callable bridge method found despite capability declaration.",
                owner="benchmark",
                detail=detail,
            )

        # ---- Leg 3: Swap on chain B ----
        leg3_t0 = time.perf_counter()
        if callable(swap_fn):
            detail["legs"]["leg3_swap"] = "attempted"
            leg3_result = await asyncio.wait_for(
                swap_fn(  # type: ignore[misc]
                    p["token_b"], p["token_a"], p["amount"], dry_run=True,
                ),
                timeout=timeout,
            )
            detail["legs"]["leg3_elapsed_ms"] = (time.perf_counter() - leg3_t0) * 1000
            detail["legs"]["leg3_result"] = str(leg3_result)[:300]
            leg3_ok = _looks_like_success(leg3_result)
            detail["legs"]["leg3_success"] = leg3_ok
        else:
            detail["legs"]["leg3_swap"] = "skipped_no_method"
            leg3_ok = True

        elapsed = (time.perf_counter() - t0) * 1000

        # ---- Evaluate atomicity ----
        all_ok = leg1_ok and leg2_ok and leg3_ok

        if all_ok:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=elapsed,
                message="Two-leg arbitrage route executed successfully; all legs passed",
                detail=detail,
                owner="provider",
            )

        # Partial failure: check rollback safety
        if not leg2_ok and _looks_like_rollback(leg2_result):
            detail["rollback_detected"] = True
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=elapsed,
                message="Bridge leg failed but safely rolled back; funds not locked",
                detail=detail,
                owner="provider",
            )

        if not leg3_ok and leg2_ok:
            # Bridge succeeded but second swap failed — potential fund lock
            detail["fund_lock_risk"] = True
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message="Partial failure: bridge succeeded but second-leg swap failed; potential fund lock risk",
                owner="provider",
                detail=detail,
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="Arbitrage route partial failure without safe rollback",
            owner="provider",
            detail=detail,
        )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Arbitrage route step timed out (>{timeout}s)",
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
            message=f"Arbitrage atomicity test failed: {exc}",
            owner="provider",
            detail=detail,
        )
