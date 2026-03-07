"""t32 — Observation: role-based access control (RBAC).

Observation-only stub.  No provider currently exposes a ``set_rbac()``
API.  Returns SKIP / UNSUPPORTED.
"""
from __future__ import annotations

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t32"
TEST_NAME = "rbac"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()

    if caps.get("set_rbac"):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="set_rbac 能力已声明但基准尚未实现完整测试逻辑。",
            owner="benchmark",
        )

    if "set_rbac" in adapter.provider_unsupported():
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            elapsed_ms=0.0,
            message="该供应商不支持角色级访问控制。",
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.SKIP,
        elapsed_ms=0.0,
        message="行业缺口：当前无供应商实现 RBAC API。",
        owner="industry",
    )
