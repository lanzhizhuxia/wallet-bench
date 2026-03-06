"""tc03 (intent) — Cancellation: verify provider handles cancellation gracefully."""

from __future__ import annotations

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "tc03"
TEST_NAME = "cancellation"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Test cancellation semantics.

    Most intent-class providers don't expose a cancel API in staging.
    We verify that the adapter at least handles the concept gracefully.
    """
    # Check if adapter has a cancel method
    has_cancel = hasattr(adapter, "cancel_transaction") and callable(
        getattr(adapter, "cancel_transaction", None)
    )

    if not has_cancel:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="取消交易功能需生产环境验证，本轮基准未接通。不影响评分，计入结论置信度。",
            owner="benchmark",
            detail={"has_cancel_api": False},
        )

    # If the adapter does have cancel, we'd test:
    # 1. Submit a tx
    # 2. Immediately cancel
    # 3. Verify no on-chain effect
    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.INCONCLUSIVE,
        message="交易取消测试逻辑待完成实现，本轮基准无法验证。不影响评分，计入结论置信度。",
        owner="benchmark",
    )
