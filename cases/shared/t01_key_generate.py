"""t01 — Wallet creation / key derivation."""

from __future__ import annotations

import re
import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t01"
TEST_NAME = "key_generate"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("create_wallet", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的钱包创建能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        info = await adapter.create_wallet()
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            message=str(exc),
        )
    elapsed = (time.perf_counter() - t0) * 1000

    address = info.address.strip()
    # Validate: must be a 0x-prefixed 40-hex-char string
    if not re.match(r"^0x[0-9a-fA-F]{40}$", address):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"地址格式无效: {address}",
            detail={"address": address},
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=f"钱包已创建 {address}",
        detail={"address": address, "chain": info.chain},
    )
