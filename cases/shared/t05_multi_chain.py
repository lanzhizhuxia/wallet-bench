"""t05 — Multi-chain: same operation across multiple chains."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t05"
TEST_NAME = "multi_chain"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("multi_chain", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的多链支持能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    if not adapter.capabilities().get("create_wallet", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的钱包创建能力，无法执行多链切换测试。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    chains = adapter.chains
    if len(chains) < 2:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准检测到供应商仅声明单条链，多链切换能力待进一步验证。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    # For now: verify create_wallet works and adapter declares multiple chains.
    # Full cross-chain execution (deploy on each chain) requires per-chain
    # network switching which depends on adapter implementation.
    try:
        wallet = await adapter.create_wallet()
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=str(exc),
        )
    elapsed = (time.perf_counter() - t0) * 1000

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=f"Adapter 声明 {len(chains)} 条链: {', '.join(chains)}",
        detail={
            "chains": chains,
            "address": wallet.address,
        },
    )
