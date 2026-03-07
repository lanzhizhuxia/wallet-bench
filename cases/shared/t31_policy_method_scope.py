"""t31 — Observation: policy engine method-level scope control.

This is an observation-only stub.  No provider currently exposes
a ``set_policy()`` API, so the test checks capabilities and returns
SKIP (industry blank) or UNSUPPORTED accordingly.
"""
from __future__ import annotations

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t31"
TEST_NAME = "policy_method_scope"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()

    if caps.get("set_policy"):
        # If a provider ever exposes set_policy, this stub should be
        # replaced with a real implementation.
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="set_policy 能力已声明但基准尚未实现完整测试逻辑。",
            owner="benchmark",
        )

    if "set_policy" in adapter.provider_unsupported():
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            elapsed_ms=0.0,
            message="该供应商不支持方法级策略控制。",
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.SKIP,
        elapsed_ms=0.0,
        message="行业缺口：当前无供应商实现方法级策略 API。",
        owner="industry",
    )
