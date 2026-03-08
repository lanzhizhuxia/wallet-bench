from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "m01"
TEST_NAME = "market_combo"

# Defaults — overridable via config["test_params"]["m01"]
_DEFAULT_PLATFORM = "polymarket"
_DEFAULT_MARKET_ID = "bench_test_market"
_DEFAULT_BET_AMOUNT = "0.01"
_DEFAULT_OUTCOME = "yes"
_DEFAULT_TIMEOUT = 30


def _provider_name(adapter: WalletAdapter) -> str:
    return f"{adapter.__class__.__name__} {getattr(adapter, 'name', '')}".lower()


def _params(config: dict) -> dict[str, Any]:
    """Extract test parameters from config with sane defaults."""
    overrides = config.get("test_params", {}).get("m01", {})
    return {
        "platform": overrides.get("platform", _DEFAULT_PLATFORM),
        "market_id": overrides.get("market_id", _DEFAULT_MARKET_ID),
        "bet_amount": overrides.get("bet_amount", _DEFAULT_BET_AMOUNT),
        "outcome": overrides.get("outcome", _DEFAULT_OUTCOME),
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
    cap_keys = ("prediction_market", "market_query", "place_bet")
    method_names = ("query_market", "place_bet", "redeem", "close_position")

    has_cap = any(caps.get(k, False) for k in cap_keys)
    has_method = any(callable(getattr(adapter, k, None)) for k in method_names)

    if not (has_cap or has_method):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="Provider does not support prediction market capabilities required for the market combo test.",
            owner="provider",
        )

    t0 = time.perf_counter()
    detail: dict[str, Any] = {
        "provider": provider,
        "params": p,
        "capabilities": {k: caps.get(k, False) for k in cap_keys},
        "methods": {k: callable(getattr(adapter, k, None)) for k in method_names},
        "steps": {},
    }

    try:
        # ---- Step 1: Query odds / market info ----
        step_t0 = time.perf_counter()
        query_fn = getattr(adapter, "query_market", None) or getattr(adapter, "prediction_market", None)
        if callable(query_fn):
            detail["steps"]["query"] = "attempted"
            query_result = await asyncio.wait_for(
                query_fn(  # type: ignore[misc]
                    platform=p["platform"],
                    market_id=p["market_id"],
                    dry_run=True,
                ),
                timeout=timeout,
            )
            detail["steps"]["query_elapsed_ms"] = (time.perf_counter() - step_t0) * 1000
            detail["steps"]["query_result"] = str(query_result)[:300]
            if not _looks_like_success(query_result):
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="Query odds step failed in market combo",
                    owner="provider",
                    detail=detail,
                )
        else:
            detail["steps"]["query"] = "skipped_no_method"

        # ---- Step 2: Place bet ----
        step_t0 = time.perf_counter()
        bet_fn = getattr(adapter, "place_bet", None)
        if callable(bet_fn):
            detail["steps"]["place_bet"] = "attempted"
            bet_result = await asyncio.wait_for(
                bet_fn(  # type: ignore[misc]
                    platform=p["platform"],
                    market_id=p["market_id"],
                    outcome=p["outcome"],
                    amount=p["bet_amount"],
                    dry_run=True,
                ),
                timeout=timeout,
            )
            detail["steps"]["place_bet_elapsed_ms"] = (time.perf_counter() - step_t0) * 1000
            detail["steps"]["place_bet_result"] = str(bet_result)[:300]
            if not _looks_like_success(bet_result):
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="Place bet step failed in market combo",
                    owner="provider",
                    detail=detail,
                )
        else:
            # place_bet is critical; if missing, check for prediction_market fallback
            pm_fn = getattr(adapter, "prediction_market", None) or getattr(adapter, "market_prediction", None)
            if callable(pm_fn):
                detail["steps"]["place_bet"] = "attempted_via_prediction_market"
                bet_result = await asyncio.wait_for(
                    pm_fn(  # type: ignore[misc]
                        platform=p["platform"], dry_run=True,
                    ),
                    timeout=timeout,
                )
                detail["steps"]["place_bet_elapsed_ms"] = (time.perf_counter() - step_t0) * 1000
                detail["steps"]["place_bet_result"] = str(bet_result)[:300]
                if not _looks_like_success(bet_result):
                    return TestResult(
                        test_id=TEST_ID,
                        test_name=TEST_NAME,
                        status=TestStatus.FAIL,
                        elapsed_ms=(time.perf_counter() - t0) * 1000,
                        message="Place bet step (via prediction_market) failed in market combo",
                        owner="provider",
                        detail=detail,
                    )
            else:
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.UNSUPPORTED,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="No callable place_bet or prediction_market method found.",
                    owner="benchmark",
                    detail=detail,
                )

        # ---- Step 3: Close position / Redeem ----
        step_t0 = time.perf_counter()
        close_fn = getattr(adapter, "close_position", None) or getattr(adapter, "redeem", None)
        if callable(close_fn):
            detail["steps"]["close"] = "attempted"
            close_result = await asyncio.wait_for(
                close_fn(  # type: ignore[misc]
                    platform=p["platform"],
                    market_id=p["market_id"],
                    dry_run=True,
                ),
                timeout=timeout,
            )
            detail["steps"]["close_elapsed_ms"] = (time.perf_counter() - step_t0) * 1000
            detail["steps"]["close_result"] = str(close_result)[:300]
            if not _looks_like_success(close_result):
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="Close/redeem step failed in market combo",
                    owner="provider",
                    detail=detail,
                )
        else:
            detail["steps"]["close"] = "skipped_no_method"

        elapsed = (time.perf_counter() - t0) * 1000
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="Full market combo (query odds -> place bet -> close/redeem) executed successfully",
            detail=detail,
            owner="provider",
        )

    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"Market combo step timed out (>{timeout}s)",
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
            message=f"Market combo execution failed: {exc}",
            owner="provider",
            detail=detail,
        )
