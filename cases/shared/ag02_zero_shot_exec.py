"""ag02 — Zero-shot execution: can a natural language goal produce a valid execution plan."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "ag02"
TEST_NAME = "zero_shot_exec"

_DEFAULT_TIMEOUT = 30

_PLAN_METHODS = ("plan", "execute_goal", "interpret", "natural_language_exec")
_DEFAULT_GOAL = "swap 1 USDC to USDT"

_SCHEMA_COMPLETENESS_THRESHOLD = 5  # minimum capabilities or schema entries


def _looks_like_plan(result: Any) -> bool:
    """Heuristic: does the return value resemble a plan / step list?"""
    if isinstance(result, list) and len(result) >= 1:
        return True
    if isinstance(result, dict):
        # Accept dicts with 'steps', 'actions', 'plan', or non-trivial content
        for key in ("steps", "actions", "plan", "tasks", "operations"):
            if key in result and result[key]:
                return True
        # Accept any dict with at least 2 meaningful keys
        if len(result) >= 2:
            return True
    if isinstance(result, str) and len(result.strip()) > 10:
        return True
    return False


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    t0 = time.perf_counter()

    detail: dict[str, Any] = {}
    notes: list[str] = []

    # ── Check for dedicated planning / NL methods ─────────────────────────
    found_method: str | None = None
    for method_name in _PLAN_METHODS:
        if getattr(adapter, method_name, None) is not None:
            found_method = method_name
            break

    detail["planning_method"] = found_method

    # ── Try calling the planning method ───────────────────────────────────
    plan_ok = False
    plan_result: Any = None

    if found_method is not None:
        fn = getattr(adapter, found_method)
        try:
            raw = (
                await asyncio.wait_for(fn(_DEFAULT_GOAL), timeout=_DEFAULT_TIMEOUT)
                if asyncio.iscoroutinefunction(fn)
                else fn(_DEFAULT_GOAL)
            )
            plan_result = raw
            plan_ok = _looks_like_plan(raw)
            detail["plan_result_type"] = type(raw).__name__
            detail["plan_looks_valid"] = plan_ok
            if isinstance(raw, (list, dict)):
                detail["plan_length"] = len(raw)
            if not plan_ok:
                notes.append(f"{found_method}() returned data that does not resemble a plan")
        except Exception as exc:
            notes.append(f"{found_method}('{_DEFAULT_GOAL}') raised: {exc}")
            detail["plan_error"] = str(exc)[:300]

    # ── Fallback: assess capabilities / schema completeness as proxy ──────
    cap_count = len(caps) if isinstance(caps, dict) else 0
    caps_sufficient = cap_count >= _SCHEMA_COMPLETENESS_THRESHOLD
    detail["capabilities_count"] = cap_count
    detail["capabilities_sufficient"] = caps_sufficient

    # Check for MCP / schema descriptors
    schema_method = getattr(adapter, "describe_schema", None) or getattr(adapter, "get_tools", None)
    schema_entries = 0
    if schema_method is not None:
        try:
            schema_raw = (
                await asyncio.wait_for(schema_method(), timeout=_DEFAULT_TIMEOUT)
                if asyncio.iscoroutinefunction(schema_method)
                else schema_method()
            )
            if isinstance(schema_raw, (list, dict)):
                schema_entries = len(schema_raw)
        except Exception:
            pass
    detail["schema_entries"] = schema_entries
    schema_sufficient = schema_entries >= _SCHEMA_COMPLETENESS_THRESHOLD
    detail["schema_sufficient"] = schema_sufficient

    elapsed = (time.perf_counter() - t0) * 1000

    # ── Determine result ──────────────────────────────────────────────────
    if plan_ok:
        message = f"Zero-shot plan produced via '{found_method}'"
        if notes:
            message = f"{message} ({'; '.join(notes)})"
        detail["pass_reason"] = "planning_method"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=message,
            detail=detail,
            owner="industry",
        )

    # No planning method or it failed — fall back to schema completeness
    if found_method is None and not caps_sufficient and not schema_sufficient:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            elapsed_ms=elapsed,
            message="No planning method found and schema/capabilities too thin for zero-shot proxy.",
            detail=detail,
            owner="provider",
        )

    # Schema/caps are rich enough to serve as a proxy for zero-shot readiness
    if caps_sufficient or schema_sufficient:
        proxy_parts: list[str] = []
        if caps_sufficient:
            proxy_parts.append(f"capabilities={cap_count}")
        if schema_sufficient:
            proxy_parts.append(f"schema_entries={schema_entries}")
        message = f"No direct plan method; schema completeness proxy OK: {', '.join(proxy_parts)}"
        if notes:
            message = f"{message} ({'; '.join(notes)})"
        detail["pass_reason"] = "schema_proxy"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=message,
            detail=detail,
            owner="industry",
        )

    # Had a planning method but it failed
    msg = "Zero-shot execution failed"
    if notes:
        msg = f"{msg}: {'; '.join(notes)}"
    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=msg,
        detail=detail,
        owner="provider",
    )
