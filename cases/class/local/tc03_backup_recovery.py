"""tc03 (local) — Backup & recovery: same key recovers same identity."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "tc03"
TEST_NAME = "backup_recovery"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Create wallet, then 'recover' by creating a second adapter instance
    with the same key and verify the address matches.
    """
    if not adapter.capabilities().get("create_wallet", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的备份恢复能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        original = await adapter.create_wallet()

        # "Recover" — create a fresh adapter instance with the same key
        adapter_class = type(adapter)
        provider_cfg = config.get("providers", {}).get("bnbchain_mcp", {})
        private_key = provider_cfg.get("private_key", "")
        network = provider_cfg.get("network", "bsc-testnet")

        recovered_adapter = adapter_class(private_key=private_key, network=network)
        await recovered_adapter.setup()
        try:
            recovered = await recovered_adapter.create_wallet()
        finally:
            await recovered_adapter.teardown()
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=str(exc),
        )
    elapsed = (time.perf_counter() - t0) * 1000

    if original.address.lower() != recovered.address.lower():
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="恢复产生了不同地址",
            detail={
                "original": original.address,
                "recovered": recovered.address,
            },
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=f"恢复已验证: {original.address}",
        detail={"address": original.address},
    )
