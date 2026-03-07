"""t30 — Submit transaction and verify receipt finality confirmations."""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any
from urllib.request import Request, urlopen

from adapters.base import _PUBLIC_RPC, TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t30"
TEST_NAME = "tx_finality"

_BURN_ADDRESS = "0x0000000000000000000000000000000000000001"


def _rpc_call(url: str, method: str, params: list[Any]) -> Any:
    payload = {"jsonrpc": "2.0", "method": method, "params": params, "id": 1}
    req = Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "wallet-bench/1.0")
    with urlopen(req, timeout=15) as resp:
        result = json.loads(resp.read())
    if "error" in result:
        raise RuntimeError(f"{method} error: {result['error']}")
    return result.get("result")


def _pick_rpc_url(config: dict, params: dict[str, Any]) -> str:
    if params.get("rpc_url"):
        return str(params["rpc_url"])
    chain = str(params.get("chain") or config.get("chain") or "ethereum-sepolia")
    if chain in _PUBLIC_RPC:
        return _PUBLIC_RPC[chain]
    return _PUBLIC_RPC["ethereum-sepolia"]


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
    min_confirmations = int(params.get("min_confirmations", 2))
    poll_interval_s = float(params.get("poll_interval_s", 2))
    rpc_url = _pick_rpc_url(config, params)

    t0 = time.perf_counter()
    try:
        tx = TxParams(to=_BURN_ADDRESS, value=0, data="0x")
        tx_result = await asyncio.wait_for(adapter.send_transaction(tx), timeout=timeout_s)
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

    if not tx_result.tx_hash:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message="交易未返回 tx_hash，无法验证最终性。",
            detail={"raw": tx_result.meta},
            owner="provider",
        )

    tx_hash = tx_result.tx_hash
    receipt: dict[str, Any] | None = None
    while (time.perf_counter() - t0) < timeout_s:
        try:
            maybe_receipt = _rpc_call(rpc_url, "eth_getTransactionReceipt", [tx_hash])
        except Exception as exc:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.ERROR,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message=f"查询 receipt 失败: {exc}",
                detail={"tx_hash": tx_hash, "rpc_url": rpc_url},
                owner="benchmark",
            )

        if isinstance(maybe_receipt, dict):
            receipt = maybe_receipt
            break
        await asyncio.sleep(poll_interval_s)

    if receipt is None:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message="超时未获取到交易 receipt。",
            detail={"tx_hash": tx_hash, "rpc_url": rpc_url},
            owner="provider",
        )

    receipt_block_hex = receipt.get("blockNumber")
    if not isinstance(receipt_block_hex, str):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message="receipt 缺少 blockNumber。",
            detail={"tx_hash": tx_hash, "receipt": receipt},
            owner="provider",
        )

    receipt_block = int(receipt_block_hex, 16)
    status_hex = receipt.get("status")
    receipt_status = int(status_hex, 16) if isinstance(status_hex, str) else None

    confirmations = 0
    while (time.perf_counter() - t0) < timeout_s:
        try:
            head_hex = _rpc_call(rpc_url, "eth_blockNumber", [])
        except Exception as exc:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.ERROR,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message=f"查询区块高度失败: {exc}",
                detail={"tx_hash": tx_hash, "rpc_url": rpc_url},
                owner="benchmark",
            )

        if isinstance(head_hex, str):
            head = int(head_hex, 16)
            confirmations = max(0, head - receipt_block + 1)
            if confirmations >= min_confirmations:
                break
        await asyncio.sleep(poll_interval_s)

    elapsed = (time.perf_counter() - t0) * 1000
    if confirmations < min_confirmations:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"确认数不足: {confirmations}/{min_confirmations}",
            detail={"tx_hash": tx_hash, "receipt_status": receipt_status, "block_number": receipt_block},
            owner="provider",
        )

    reverted = receipt_status == 0 or bool(tx_result.meta.get("revert", False))
    message = "交易已最终确认" if not reverted else "交易已最终确认（执行 revert 但最终性链路正常）"
    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message=message,
        detail={
            "tx_hash": tx_hash,
            "receipt_status": receipt_status,
            "block_number": receipt_block,
            "confirmations": confirmations,
            "rpc_url": rpc_url,
            "revert": reverted,
        },
        owner="provider",
    )
