"""ag01 — Tool discovery: can the adapter enumerate callable methods and parameter schemas."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "ag01"
TEST_NAME = "tool_discovery"

_DEFAULT_TIMEOUT = 30

_TOOL_LIST_METHODS = ("list_tools", "describe_schema", "get_tools", "tool_list")

_MIN_CAP_ENTRIES = 8
_MIN_PUBLIC_METHODS = 9  # ISSUE-028: lowered from 10 to allow adapters with 9 methods (e.g. Coinbase, Privy) to pass

# Key wallet methods that must be present for introspection to count as meaningful
# (prevents adapters that merely "pad" base class methods from passing)
_REQUIRED_METHODS: frozenset[str] = frozenset({
    'create_wallet', 'sign_message', 'send_transaction', 'capabilities',
})


def _count_public_methods(adapter: WalletAdapter) -> list[str]:
    """Return names of public callable methods (not starting with _)."""
    return [
        name
        for name in dir(adapter)
        if not name.startswith("_") and callable(getattr(adapter, name, None))
    ]


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    t0 = time.perf_counter()

    detail: dict[str, Any] = {}
    notes: list[str] = []

    # ── Check for dedicated tool-listing methods ──────────────────────────
    found_method: str | None = None
    for method_name in _TOOL_LIST_METHODS:
        if getattr(adapter, method_name, None) is not None:
            found_method = method_name
            break

    detail["dedicated_tool_method"] = found_method

    tool_list_result: Any = None
    tool_list_ok = False

    if found_method is not None:
        fn = getattr(adapter, found_method)
        try:
            raw = fn() if not asyncio.iscoroutinefunction(fn) else await asyncio.wait_for(fn(), timeout=_DEFAULT_TIMEOUT)
            tool_list_result = raw
            # Accept list, dict, or any non-empty structured data
            if isinstance(raw, (list, dict)):
                tool_list_ok = len(raw) > 0
            elif raw is not None:
                tool_list_ok = bool(raw)
            detail["tool_list_result_type"] = type(raw).__name__
            detail["tool_list_length"] = len(raw) if isinstance(raw, (list, dict)) else None
        except Exception as exc:
            notes.append(f"{found_method}() raised: {exc}")
            detail["tool_list_error"] = str(exc)[:300]

    # ── Introspect capabilities() completeness ────────────────────────────
    cap_count = len(caps) if isinstance(caps, dict) else 0
    caps_rich = cap_count >= _MIN_CAP_ENTRIES
    detail["capabilities_count"] = cap_count
    detail["capabilities_rich"] = caps_rich

    # ── Count public callable methods + key method guard (ISSUE-028) ───────
    public_methods = _count_public_methods(adapter)
    public_count = len(public_methods)
    public_methods_set = set(public_methods)
    has_enough_public = public_count >= _MIN_PUBLIC_METHODS
    has_required_methods = _REQUIRED_METHODS.issubset(public_methods_set)
    detail["public_method_count"] = public_count
    detail["public_methods"] = public_methods[:20]  # cap for readability
    detail["required_methods_present"] = sorted(_REQUIRED_METHODS & public_methods_set)
    detail["required_methods_missing"] = sorted(_REQUIRED_METHODS - public_methods_set)

    elapsed = (time.perf_counter() - t0) * 1000

    # ── Determine result ──────────────────────────────────────────────────
    # PASS if: dedicated tool list method returning structured data,
    #   OR capabilities() >= 5 entries AND >= 5 public callable methods
    pass_via_tool_list = tool_list_ok
    pass_via_introspection = caps_rich and has_enough_public and has_required_methods  # ISSUE-028: added key method guard

    if not pass_via_tool_list and not pass_via_introspection:
        # Neither path satisfied — UNSUPPORTED if no tool method exists and
        # introspection is too thin; otherwise FAIL.
        if found_method is None and not caps_rich:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=elapsed,
                message="No tool listing method found and capabilities() too sparse for discovery.",
                detail=detail,
                owner="provider",
            )
        msg = "Tool discovery insufficient"
        if notes:
            msg = f"{msg}; {'; '.join(notes)}"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=msg,
            detail=detail,
            owner="provider",
        )

    # ── Scoring / message ─────────────────────────────────────────────────
    score_parts: list[str] = []
    if pass_via_tool_list and pass_via_introspection:
        score_parts.append("full discovery")
        score_parts.append(f"dedicated method '{found_method}' + capabilities={cap_count}, public_methods={public_count}")
        detail["discovery_quality"] = "full"
    elif pass_via_tool_list:
        score_parts.append("dedicated method only")
        score_parts.append(f"'{found_method}' returned structured data")
        detail["discovery_quality"] = "dedicated"
    elif pass_via_introspection:
        score_parts.append("introspection only")
        score_parts.append(f"capabilities={cap_count}, public_methods={public_count}")
        detail["discovery_quality"] = "basic"

    message = f"Tool discovery OK: {'; '.join(score_parts)}"
    if notes:
        message = f"{message} ({'; '.join(notes)})"

    detail["pass_via_tool_list"] = pass_via_tool_list
    detail["pass_via_introspection"] = pass_via_introspection

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=message,
        detail=detail,
        owner="industry",
    )
