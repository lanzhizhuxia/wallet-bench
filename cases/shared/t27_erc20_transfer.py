"""t27 — Build ERC-20 transfer calldata and submit transaction."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t27"
TEST_NAME = "erc20_transfer"

_BURN_ADDRESS = "0x000000000000000000000000000000000000dEaD"
_TOKEN_CONTRACT = "0x0000000000000000000000000000000000000001"
_TRANSFER_SELECTOR = "a9059cbb"


def _encode_erc20_transfer(to_addr: str, amount: int) -> str:
    addr = to_addr.lower().removeprefix("0x")
    if len(addr) != 40:
        raise ValueError("invalid transfer recipient address")
    if amount < 0:
        raise ValueError("amount must be non-negative")
    addr_word = addr.rjust(64, "0")
    amount_word = hex(amount)[2:].rjust(64, "0")
    return f"0x{_TRANSFER_SELECTOR}{addr_word}{amount_word}"


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

    t0 = time.perf_counter()
    try:
        wallet = await asyncio.wait_for(adapter.create_wallet(), timeout=timeout_s)
        calldata = _encode_erc20_transfer(_BURN_ADDRESS, 1)
        tx = TxParams(to=_TOKEN_CONTRACT, value=0, data=calldata)
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
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=str(exc),
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
            message="未返回 tx_hash 且未识别到 revert。",
            detail={"raw": result.meta, "calldata": calldata, "wallet": wallet.address},
            owner="provider",
        )

    if is_revert:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="交易提交成功但执行 revert（预期可接受）。",
            detail={"revert": True, "tx_hash": result.tx_hash, "calldata": calldata, "wallet": wallet.address},
            owner="provider",
        )

    detail: dict[str, Any] = {
        "tx_hash": result.tx_hash,
        "calldata": calldata,
        "wallet": wallet.address,
    }
    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=f"ERC-20 transfer calldata 已提交: {result.tx_hash}",
        detail=detail,
        owner="provider",
    )
