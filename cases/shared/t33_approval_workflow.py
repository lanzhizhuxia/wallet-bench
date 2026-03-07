"""t33 — Observation: multi-signature approval workflow.

Observation-only stub.  No provider currently exposes a
``request_approval()`` API.  Returns SKIP / UNSUPPORTED.
"""
from __future__ import annotations

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t33"
TEST_NAME = "approval_workflow"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()

    if caps.get("request_approval"):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="request_approval 能力已声明但基准尚未实现完整测试逻辑。",
            owner="benchmark",
        )

    if "request_approval" in adapter.provider_unsupported():
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            elapsed_ms=0.0,
            message="该供应商不支持审批工作流。",
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.SKIP,
        elapsed_ms=0.0,
        message="行业缺口：当前无供应商实现审批工作流 API。",
        owner="industry",
    )
