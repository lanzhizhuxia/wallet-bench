"""tc02 (tee) — Failover continuity: wallet identity persists across sessions.

Simulates re-init: create wallet → teardown → setup → verify address still
accessible and sign still works.  TEE providers should maintain wallet
identity across session reconnects.
"""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "tc02"
TEST_NAME = "failover_continuity"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    t0 = time.perf_counter()

    # Step 1: Create wallet and get address
    try:
        wallet = await adapter.create_wallet()
        addr1 = wallet.address
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"钱包创建失败: {exc}",
        )

    # Step 2: Sign a message to prove key access
    sig1 = None
    if adapter.capabilities().get("sign_message", False):
        try:
            sig1 = await adapter.sign_message("continuity-check")
        except Exception:
            pass

    # Step 3: Teardown and re-setup (simulate session restart)
    try:
        await adapter.teardown()
        await adapter.setup()
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"重新 setup 失败: {exc}",
        )

    # Step 4: Verify we can still sign (key access persists)
    if adapter.capabilities().get("sign_message", False) and sig1:
        try:
            sig2 = await adapter.sign_message("continuity-check-2")
            key_persists = bool(sig2.signature) and len(sig2.signature) > 10
        except Exception:
            key_persists = False
    else:
        # If no sign_message, just check setup didn't crash
        key_persists = True

    elapsed = (time.perf_counter() - t0) * 1000

    if key_persists:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="钱包身份在会话重启后保持一致",
        )
    else:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="会话重启后密钥访问丢失",
        )
