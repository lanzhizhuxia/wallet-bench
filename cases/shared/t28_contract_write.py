"""t28 — Submit contract write transaction with non-empty calldata."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t28"
TEST_NAME = "contract_write"

_TARGET_ADDRESS = "0x0000000000000000000000000000000000000001"
_INCREMENT_SELECTOR = "0xd09de08a"


def _looks_like_revert(message: str) -> bool:
    lowered = message.lower()
    return "revert" in lowered or "execution reverted" in lowered


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("send_transaction", False):
        if "send_transaction" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=0.0,
                message="该供应商不支持交易发送能力。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="本轮基准未接入该供应商的交易发送能力，无法验证。",
            owner="benchmark",
        )

    params = config.get("test_params", {}).get(TEST_ID, {})
    timeout_s = float(params.get("timeout_s", 60))
    target = str(params.get("target_address", _TARGET_ADDRESS))
    calldata = str(params.get("calldata", _INCREMENT_SELECTOR))

    t0 = time.perf_counter()
    try:
        tx = TxParams(to=target, value=0, data=calldata)
        result = await asyncio.wait_for(adapter.send_transaction(tx), timeout=timeout_s)
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
        elapsed = (time.perf_counter() - t0) * 1000
        if _looks_like_revert(str(exc)):
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=elapsed,
                message="合约写入调用触发 revert（预期可接受）。",
                detail={"revert": True, "error": str(exc), "data": calldata, "to": target},
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"发送含 data 交易失败: {exc}",
            detail={"data": calldata, "to": target},
            owner="provider",
        )

    elapsed = (time.perf_counter() - t0) * 1000
    is_revert = bool(result.meta.get("revert", False)) or result.status == 0

    if not result.tx_hash and not is_revert:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="未返回 tx_hash 且未识别到 revert，无法确认 data 交易提交。",
            detail={"raw": result.meta, "data": calldata, "to": target},
            owner="provider",
        )

    detail: dict[str, Any] = {
        "tx_hash": result.tx_hash,
        "revert": is_revert,
        "data": calldata,
        "to": target,
    }
    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message="含 calldata 的交易可被适配器处理并提交。",
        detail=detail,
        owner="provider",
    )
