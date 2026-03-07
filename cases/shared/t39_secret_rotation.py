"""t39 — Observation: secret / credential rotation.

Observation-only stub.  No provider currently exposes a
``rotate_secret()`` API.  Returns SKIP / UNSUPPORTED.
"""
from __future__ import annotations

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t39"
TEST_NAME = "secret_rotation"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()

    if caps.get("rotate_secret"):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="rotate_secret 能力已声明但基准尚未实现完整测试逻辑。",
            owner="benchmark",
        )

    if "rotate_secret" in adapter.provider_unsupported():
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            elapsed_ms=0.0,
            message="该供应商不支持密钥/凭证轮换。",
            owner="provider",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.SKIP,
        elapsed_ms=0.0,
        message="行业缺口：当前无供应商实现密钥轮换 API。",
        owner="industry",
    )
