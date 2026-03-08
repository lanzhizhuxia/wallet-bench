"""ag04 — Multi-step plan: verify Agent can generate a correct multi-step plan."""
from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "ag04"
TEST_NAME = "multi_step_plan"

_DEFAULT_TIMEOUT = 30

_PLANNING_METHODS = ("plan", "multi_step_plan", "create_plan", "execute_goal")
_MULTI_STEP_CAPABILITIES = ("swap", "token_swap", "bridge", "cross_chain_bridge",
                            "stake", "staking", "approve", "send_transaction")

_TEST_GOAL = "approve USDC, swap to ETH, bridge to Arbitrum, stake in Aave"
_EXPECTED_ORDER = ["approve", "swap", "bridge", "stake"]


def _params(config: dict) -> dict[str, Any]:
    return config.get("test_params", {}).get("ag04", {})


def _find_planning_method(adapter: WalletAdapter) -> tuple[str | None, Any]:
    """Return (method_name, bound_method) for the first available planning method."""
    for name in _PLANNING_METHODS:
        method = getattr(adapter, name, None)
        if callable(method):
            return name, method
    return None, None


def _count_multi_step_capabilities(adapter: WalletAdapter) -> list[str]:
    """Return list of capabilities that could support multi-step flows."""
    caps = adapter.capabilities()
    found: list[str] = []
    for cap in _MULTI_STEP_CAPABILITIES:
        if caps.get(cap, False):
            found.append(cap)
    for method_name in ("swap", "token_swap", "bridge", "cross_chain_bridge",
                        "stake", "staking", "approve"):
        if callable(getattr(adapter, method_name, None)) and method_name not in found:
            found.append(method_name)
    return found


def _validate_plan_steps(plan: Any) -> dict[str, Any]:
    """Validate that the plan has correct step order and dependency relationships.

    Returns a dict with validation results.
    """
    result: dict[str, Any] = {
        "valid": False,
        "steps_found": [],
        "order_correct": False,
        "has_dependencies": False,
        "notes": [],
    }

    steps: list[Any] = []
    if isinstance(plan, list):
        steps = plan
    elif isinstance(plan, dict):
        steps = plan.get("steps", plan.get("plan", plan.get("actions", [])))
        if isinstance(steps, dict):
            steps = list(steps.values())
    elif hasattr(plan, "steps"):
        steps = getattr(plan, "steps", [])

    if not steps:
        result["notes"].append("No steps found in plan output")
        return result

    # Extract step labels/names
    step_labels: list[str] = []
    for step in steps:
        label = ""
        if isinstance(step, str):
            label = step.lower()
        elif isinstance(step, dict):
            label = str(step.get("action", step.get("name", step.get("type", "")))).lower()
        elif hasattr(step, "action"):
            label = str(getattr(step, "action", "")).lower()
        step_labels.append(label)

    result["steps_found"] = step_labels

    # Check order: approve must come before swap, swap before bridge, bridge before stake
    order_positions: dict[str, int] = {}
    for keyword in _EXPECTED_ORDER:
        for i, label in enumerate(step_labels):
            if keyword in label:
                order_positions[keyword] = i
                break

    matched = [k for k in _EXPECTED_ORDER if k in order_positions]
    result["matched_steps"] = matched

    if len(matched) >= 2:
        positions = [order_positions[k] for k in _EXPECTED_ORDER if k in order_positions]
        result["order_correct"] = positions == sorted(positions)
    else:
        result["notes"].append(f"Only {len(matched)} of 4 expected steps matched")

    # Check for dependency info
    for step in steps:
        if isinstance(step, dict):
            if any(k in step for k in ("depends_on", "dependencies", "requires", "after")):
                result["has_dependencies"] = True
                break

    result["valid"] = result["order_correct"] and len(matched) >= 2
    return result


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Test whether the adapter can generate a correct multi-step execution plan.

    Given a multi-step goal (approve -> swap -> bridge -> stake), verify the
    generated plan has correct step order and dependency relationships.
    """
    params = _params(config)
    timeout = params.get("timeout", _DEFAULT_TIMEOUT)

    t0 = time.perf_counter()
    detail: dict[str, Any] = {}

    # Check for explicit planning methods
    method_name, planning_method = _find_planning_method(adapter)

    if planning_method is not None:
        detail["planning_method"] = method_name
        try:
            # Determine how to call the planning method
            sig = inspect.signature(planning_method)
            param_names = list(sig.parameters.keys())

            if "goal" in param_names:
                plan = await asyncio.wait_for(
                    planning_method(goal=_TEST_GOAL),
                    timeout=timeout,
                )
            elif len(param_names) >= 1:
                plan = await asyncio.wait_for(
                    planning_method(_TEST_GOAL),
                    timeout=timeout,
                )
            else:
                plan = await asyncio.wait_for(
                    planning_method(),
                    timeout=timeout,
                )

            elapsed = (time.perf_counter() - t0) * 1000
            detail["raw_plan"] = str(plan)[:500]

            validation = _validate_plan_steps(plan)
            detail["validation"] = validation

            if validation["valid"]:
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.PASS,
                    elapsed_ms=elapsed,
                    message=f"Multi-step plan generated with correct order: {validation['matched_steps']}",
                    detail=detail,
                    owner="provider",
                )
            else:
                notes = "; ".join(validation["notes"]) if validation["notes"] else "step order invalid"
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=elapsed,
                    message=f"Plan generated but validation failed: {notes}",
                    detail=detail,
                    owner="provider",
                )

        except asyncio.TimeoutError:
            elapsed = (time.perf_counter() - t0) * 1000
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message=f"Planning method '{method_name}' timed out after {timeout}s",
                detail=detail,
                owner="provider",
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            detail["error"] = str(exc)[:300]
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message=f"Planning method '{method_name}' raised error: {exc}",
                detail=detail,
                owner="provider",
            )

    # No explicit planning method — check if adapter has sufficient multi-step capabilities
    multi_caps = _count_multi_step_capabilities(adapter)
    detail["available_multi_step_capabilities"] = multi_caps

    elapsed = (time.perf_counter() - t0) * 1000

    if len(multi_caps) >= 3:
        detail["note"] = (
            "Adapter has sufficient capabilities for multi-step flows "
            "but no explicit planning method was found."
        )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=(
                f"No planning method found, but adapter has {len(multi_caps)} "
                f"relevant capabilities ({', '.join(multi_caps)}). "
                "A planning API would enable multi-step orchestration."
            ),
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.UNSUPPORTED,
        elapsed_ms=elapsed,
        message=(
            f"No planning method and insufficient capability coverage "
            f"({len(multi_caps)}/3 required). Multi-step planning not feasible."
        ),
        detail=detail,
        owner="provider",
    )
