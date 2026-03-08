"""ag05 — Context efficiency: measure how many tokens are needed to describe the API."""
from __future__ import annotations

import inspect
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "ag05"
TEST_NAME = "context_efficiency"

_TOKEN_THRESHOLD = 2000


def _params(config: dict) -> dict[str, Any]:
    return config.get("test_params", {}).get("ag05", {})


def _get_public_methods(adapter: WalletAdapter) -> list[str]:
    """Return names of public (non-underscore) callable methods."""
    methods: list[str] = []
    for name in dir(adapter):
        if name.startswith("_"):
            continue
        if callable(getattr(adapter, name, None)):
            methods.append(name)
    return methods


def _gather_api_text(adapter: WalletAdapter) -> dict[str, Any]:
    """Gather all text that describes the adapter's complete API surface.

    Returns a dict with text segments and their individual token estimates.
    """
    segments: dict[str, str] = {}

    # 1. Capabilities keys and values
    caps = adapter.capabilities()
    caps_text = " ".join(f"{k}={v}" for k, v in caps.items())
    segments["capabilities"] = caps_text

    # 2. Public method names
    methods = _get_public_methods(adapter)
    segments["method_names"] = " ".join(methods)

    # 3. Docstrings from public methods
    docstrings: list[str] = []
    for method_name in methods:
        method = getattr(adapter, method_name, None)
        if method is not None and callable(method):
            doc = inspect.getdoc(method)
            if doc:
                docstrings.append(f"{method_name}: {doc}")
    segments["docstrings"] = " ".join(docstrings)

    # 4. Method signatures
    signatures: list[str] = []
    for method_name in methods:
        method = getattr(adapter, method_name, None)
        if method is not None and callable(method):
            try:
                sig = inspect.signature(method)
                signatures.append(f"{method_name}{sig}")
            except (ValueError, TypeError):
                signatures.append(method_name)
    segments["signatures"] = " ".join(signatures)

    # 5. Schema if available
    schema_method = (
        getattr(adapter, "get_openai_schema", None)
        or getattr(adapter, "get_mcp_schema", None)
        or getattr(adapter, "tools_schema", None)
        or getattr(adapter, "to_function_calling", None)
        or getattr(adapter, "schema", None)
    )
    if callable(schema_method):
        try:
            schema = schema_method()
            segments["schema"] = str(schema)
        except Exception:
            pass

    # 6. Class-level attributes
    attrs: list[str] = []
    for attr_name in ("name", "arch_class", "chains", "custody_model",
                      "signing_modes", "submission_mode"):
        val = getattr(adapter, attr_name, None)
        if val:
            attrs.append(f"{attr_name}={val}")
    segments["class_attributes"] = " ".join(attrs)

    return segments


def _estimate_tokens(text: str) -> int:
    """Rough token estimation: len(text) / 4."""
    return len(text) // 4


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Measure how many tokens are needed to describe the adapter's complete API.

    A lower token count means the API is more efficient to include in an LLM
    context window, making it cheaper and faster for Agent-based usage.
    """
    params = _params(config)
    threshold = params.get("token_threshold", _TOKEN_THRESHOLD)

    t0 = time.perf_counter()

    segments = _gather_api_text(adapter)

    # Calculate per-segment token counts
    breakdown: dict[str, int] = {}
    total_text = ""
    for segment_name, text in segments.items():
        tokens = _estimate_tokens(text)
        breakdown[segment_name] = tokens
        total_text += text + " "

    total_tokens = _estimate_tokens(total_text)

    elapsed = (time.perf_counter() - t0) * 1000

    detail: dict[str, Any] = {
        "total_tokens": total_tokens,
        "threshold": threshold,
        "breakdown": breakdown,
        "total_chars": len(total_text),
        "method_count": len(_get_public_methods(adapter)),
        "capability_count": len(adapter.capabilities()),
    }

    if total_tokens <= threshold:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=(
                f"API description fits in {total_tokens} tokens "
                f"(threshold: {threshold}). Efficient for LLM context."
            ),
            detail=detail,
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=(
            f"API description requires {total_tokens} tokens "
            f"(threshold: {threshold}). Consider reducing API surface "
            "or improving documentation conciseness."
        ),
        detail=detail,
        owner="provider",
    )
