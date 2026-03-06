"""t07 — Session delegation (scoped agent permissions)."""

from __future__ import annotations

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t07"
TEST_NAME = "session_delegation"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("session_delegation", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.SKIP,
            message="行业现状：目前所有评测供应商均未提供会话委托/权限代理功能。作为市场成熟度观察指标保留。",
            owner="industry",
        )

    # TODO: When we have a provider that supports delegation:
    # 1. Create scoped session (time-limited, amount-limited)
    # 2. Operate within scope → success
    # 3. Operate outside scope → failure
    # 4. Revoke session → verify revocation within SLA
    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.SKIP,
        message="行业现状：会话委托功能尚无供应商支持完整实现，测试逻辑待接入。",
        owner="industry",
    )
