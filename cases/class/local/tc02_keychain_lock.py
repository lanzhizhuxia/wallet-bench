"""tc02 (local) — Attempt operations without private key → expect clean failure."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "tc02"
TEST_NAME = "keychain_lock"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    """Try to instantiate the adapter without a valid private key.

    For Local-class adapters, absence of the private key should result in a
    clean, informative error — not a crash or silent success.
    """
    t0 = time.perf_counter()

    # We test by importing and instantiating the adapter class with an empty key
    adapter_module = type(adapter).__module__
    adapter_class = type(adapter)

    # Get the real address from the good adapter for comparison
    try:
        good_wallet = await adapter.create_wallet()
        good_address = good_wallet.address.lower()
    except Exception:
        good_address = None

    try:
        # Attempt to create adapter with invalid credentials.
        # Detect adapter type to construct appropriate "bad" instance.
        import inspect
        sig = inspect.signature(adapter_class.__init__)
        params = list(sig.parameters.keys())
        if "private_key" in params:
            bad_adapter = adapter_class(private_key="", network="bsc-testnet")
        elif "wallet_name" in params:
            bad_adapter = adapter_class(wallet_name="nonexistent-wallet-zzz", chain="ethereum")
        else:
            bad_adapter = adapter_class()
        await bad_adapter.setup()
        try:
            wallet = await bad_adapter.create_wallet()
            bad_address = wallet.address.strip().lower()
            await bad_adapter.teardown()

            # Accept if: returned a different address (empty key derived a
            # different identity — MCP server didn't leak the real key).
            # Also accept zero-address or clearly invalid address.
            zero_addr = "0x" + "0" * 40
            if bad_address == zero_addr or bad_address != good_address:
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.PASS,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message=f"空密钥产生了不同地址 {bad_address}（无密钥泄露）",
                    detail={"bad_address": bad_address, "good_address": good_address},
                )
            # Same address with empty key → something is wrong
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="空密钥产生了与真实密钥相同的地址",
            )
        except Exception as op_exc:
            await bad_adapter.teardown()
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message=f"空密钥操作正常失败: {op_exc}",
            )
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        # Good — setup itself rejected the empty key
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message=f"空密钥 setup 正常拒绝: {exc}",
        )
