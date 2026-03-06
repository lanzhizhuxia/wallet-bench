"""t03 — Sign EIP-712 typed data."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t03"
TEST_NAME = "sign_typed_data"

# Minimal EIP-712 typed data for testing
_SAMPLE_TYPED_DATA = {
    "types": {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "Test": [
            {"name": "message", "type": "string"},
            {"name": "value", "type": "uint256"},
        ],
    },
    "primaryType": "Test",
    "domain": {
        "name": "wallet-bench",
        "version": "1",
        "chainId": 97,
        "verifyingContract": "0x0000000000000000000000000000000000000001",
    },
    "message": {"message": "hello", "value": 1},
}


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("sign_typed_data", False):
        if "sign_typed_data" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持 EIP-712 结构化数据签名。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的结构化数据签名 (EIP-712) 能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        result = await adapter.sign_typed_data(_SAMPLE_TYPED_DATA)
    except NotImplementedError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message="基准侧声明支持但未完成实现，结果待确认。",
            owner="benchmark",
        )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=str(exc),
        )
    elapsed = (time.perf_counter() - t0) * 1000

    if not result.signature:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="返回了空签名",
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message="EIP-712 签名成功",
        detail={"signature": result.signature, "signer": result.signer},
    )
