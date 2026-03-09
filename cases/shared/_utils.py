"""Shared utilities for wallet-bench test cases (ISSUE-028 P2-1).

Extracted from duplicated implementations across d01, m01, x01, t16, t17, t18.
"""
from __future__ import annotations

from typing import Any


def looks_like_success(result: Any) -> bool:
    """Heuristic: check that the result doesn't indicate a hidden failure.

    Checks both structured fields (success, status) and raw string signals.
    """
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
