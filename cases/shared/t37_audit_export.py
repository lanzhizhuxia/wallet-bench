"""t37 — Observation: audit log export.

Observation-only stub.  No provider currently exposes an
``export_audit_logs()`` API.  Returns SKIP / UNSUPPORTED.
"""
from __future__ import annotations

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t37"
TEST_NAME = "audit_export"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()

    if caps.get("export_audit_logs"):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="export_audit_logs 能力已声明但基准尚未实现完整测试逻辑。",
            owner="benchmark",
        )

    if "export_audit_logs" in adapter.provider_unsupported():
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            elapsed_ms=0.0,
            message="该供应商不支持审计日志导出。",
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.SKIP,
        elapsed_ms=0.0,
        message="行业缺口：当前无供应商实现审计日志导出 API。",
        owner="industry",
    )
