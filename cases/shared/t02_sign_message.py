"""t02 — Sign an arbitrary message (personal_sign / EIP-191)."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t02"
TEST_NAME = "sign_message"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("sign_message", False):
        if "sign_message" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持消息签名 (personal_sign / EIP-191)。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的消息签名能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        result = await adapter.sign_message("hello wallet-bench")
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
        message="消息签名成功",
        detail={"signature": result.signature, "signer": result.signer},
    )
