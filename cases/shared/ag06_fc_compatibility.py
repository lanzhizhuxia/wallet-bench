"""ag06 — Function calling compatibility: OpenAI function calling + MCP protocol."""
from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "ag06"
TEST_NAME = "fc_compatibility"

_DEFAULT_TIMEOUT = 30

_SCHEMA_METHODS = (
    "get_openai_schema",
    "get_mcp_schema",
    "to_function_calling",
    "tools_schema",
)


def _params(config: dict) -> dict[str, Any]:
    return config.get("test_params", {}).get("ag06", {})


def _find_schema_method(adapter: WalletAdapter) -> tuple[str | None, Any]:
    """Return (method_name, bound_method) for the first available schema export."""
    for name in _SCHEMA_METHODS:
        method = getattr(adapter, name, None)
        if callable(method):
            return name, method
    return None, None


def _validate_openai_schema(schema: Any) -> dict[str, Any]:
    """Validate that a schema conforms to OpenAI function calling format.

    Expected structure (per tool):
    {
        "name": "...",
        "description": "...",
        "parameters": { "type": "object", "properties": {...} }
    }
    """
    result: dict[str, Any] = {
        "format": "openai",
        "valid": False,
        "tools_count": 0,
        "issues": [],
    }

    tools: list[Any] = []
    if isinstance(schema, list):
        tools = schema
    elif isinstance(schema, dict):
        if "name" in schema and "parameters" in schema:
            tools = [schema]
        elif "functions" in schema:
            tools = schema["functions"]
        elif "tools" in schema:
            tools = schema["tools"]

    result["tools_count"] = len(tools)

    if not tools:
        result["issues"].append("No tool definitions found in schema")
        return result

    valid_count = 0
    for i, tool in enumerate(tools):
        tool_def = tool
        # Handle wrapper: {"type": "function", "function": {...}}
        if isinstance(tool, dict) and "function" in tool:
            tool_def = tool["function"]

        if not isinstance(tool_def, dict):
            result["issues"].append(f"Tool {i}: not a dict")
            continue

        if "name" not in tool_def:
            result["issues"].append(f"Tool {i}: missing 'name' field")
            continue

        if "parameters" not in tool_def:
            result["issues"].append(f"Tool {i} ({tool_def.get('name', '?')}): missing 'parameters' field")
            continue

        params = tool_def["parameters"]
        if isinstance(params, dict) and params.get("type") == "object":
            valid_count += 1
        else:
            result["issues"].append(
                f"Tool {i} ({tool_def.get('name', '?')}): 'parameters' should have type='object'"
            )

    result["valid"] = valid_count > 0 and len(result["issues"]) == 0
    result["valid_tools"] = valid_count
    return result


def _validate_mcp_schema(schema: Any) -> dict[str, Any]:
    """Validate that a schema conforms to MCP tool format.

    Expected structure (per tool):
    {
        "name": "...",
        "description": "...",
        "inputSchema": { "type": "object", "properties": {...} }
    }
    """
    result: dict[str, Any] = {
        "format": "mcp",
        "valid": False,
        "tools_count": 0,
        "issues": [],
    }

    tools: list[Any] = []
    if isinstance(schema, list):
        tools = schema
    elif isinstance(schema, dict):
        if "name" in schema and "inputSchema" in schema:
            tools = [schema]
        elif "tools" in schema:
            tools = schema["tools"]

    result["tools_count"] = len(tools)

    if not tools:
        result["issues"].append("No MCP tool definitions found in schema")
        return result

    valid_count = 0
    for i, tool in enumerate(tools):
        if not isinstance(tool, dict):
            result["issues"].append(f"Tool {i}: not a dict")
            continue

        if "name" not in tool:
            result["issues"].append(f"Tool {i}: missing 'name' field")
            continue

        if "inputSchema" not in tool:
            result["issues"].append(f"Tool {i} ({tool.get('name', '?')}): missing 'inputSchema' field")
            continue

        input_schema = tool["inputSchema"]
        if isinstance(input_schema, dict) and input_schema.get("type") == "object":
            valid_count += 1
        else:
            result["issues"].append(
                f"Tool {i} ({tool.get('name', '?')}): 'inputSchema' should have type='object'"
            )

    result["valid"] = valid_count > 0 and len(result["issues"]) == 0
    result["valid_tools"] = valid_count
    return result


def _assess_auto_schema_potential(adapter: WalletAdapter) -> dict[str, Any]:
    """Check if capabilities + method signatures are rich enough to auto-generate schema."""
    caps = adapter.capabilities()
    methods: list[str] = []
    typed_methods = 0

    for name in dir(adapter):
        if name.startswith("_"):
            continue
        method = getattr(adapter, name, None)
        if not callable(method):
            continue
        methods.append(name)
        try:
            sig = inspect.signature(method)
            hints = {k: v.annotation for k, v in sig.parameters.items()
                     if v.annotation is not inspect.Parameter.empty}
            if hints:
                typed_methods += 1
        except (ValueError, TypeError):
            pass

    has_docstrings = 0
    for name in methods:
        method = getattr(adapter, name, None)
        if method and inspect.getdoc(method):
            has_docstrings += 1

    rich_enough = (
        len(caps) >= 3
        and len(methods) >= 3
        and (typed_methods >= 2 or has_docstrings >= 2)
    )

    return {
        "capability_count": len(caps),
        "method_count": len(methods),
        "typed_methods": typed_methods,
        "documented_methods": has_docstrings,
        "auto_schema_feasible": rich_enough,
    }


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Test OpenAI function calling and MCP protocol compatibility.

    Checks whether the adapter exports schemas in standard formats that
    enable LLM-based agents to invoke wallet operations via function calling.
    """
    params = _params(config)
    timeout = params.get("timeout", _DEFAULT_TIMEOUT)

    t0 = time.perf_counter()
    detail: dict[str, Any] = {}

    # Check for explicit schema export methods
    method_name, schema_method = _find_schema_method(adapter)

    if schema_method is not None:
        detail["schema_method"] = method_name
        try:
            # Call the schema method (may be sync or async)
            if asyncio.iscoroutinefunction(schema_method):
                schema = await asyncio.wait_for(schema_method(), timeout=timeout)
            else:
                schema = schema_method()

            detail["raw_schema_preview"] = str(schema)[:500]

            # Try OpenAI format validation first
            openai_result = _validate_openai_schema(schema)
            mcp_result = _validate_mcp_schema(schema)

            detail["openai_validation"] = openai_result
            detail["mcp_validation"] = mcp_result

            elapsed = (time.perf_counter() - t0) * 1000

            if openai_result["valid"] or mcp_result["valid"]:
                formats: list[str] = []
                if openai_result["valid"]:
                    formats.append(f"OpenAI ({openai_result['valid_tools']} tools)")
                if mcp_result["valid"]:
                    formats.append(f"MCP ({mcp_result['valid_tools']} tools)")

                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.PASS,
                    elapsed_ms=elapsed,
                    message=f"Schema export valid: {', '.join(formats)}",
                    detail=detail,
                    owner="provider",
                )

            # Schema returned but neither format validated
            all_issues = openai_result["issues"] + mcp_result["issues"]
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message=(
                    f"Schema method '{method_name}' returned data but "
                    f"failed validation: {'; '.join(all_issues[:3])}"
                ),
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
                message=f"Schema method '{method_name}' timed out after {timeout}s",
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
                message=f"Schema method '{method_name}' raised error: {exc}",
                detail=detail,
                owner="provider",
            )

    # No explicit schema method — assess auto-generation potential
    auto_assessment = _assess_auto_schema_potential(adapter)
    detail["auto_schema_assessment"] = auto_assessment

    elapsed = (time.perf_counter() - t0) * 1000

    if auto_assessment["auto_schema_feasible"]:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=(
                f"No schema export method found, but adapter has "
                f"{auto_assessment['method_count']} methods with "
                f"{auto_assessment['typed_methods']} typed and "
                f"{auto_assessment['documented_methods']} documented. "
                "Auto-generating an OpenAI/MCP schema is feasible."
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
            "No schema export method and insufficient method metadata "
            "for auto-generation. Function calling compatibility not feasible."
        ),
        detail=detail,
        owner="provider",
    )
