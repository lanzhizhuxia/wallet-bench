"""t20 — Transaction confirmation: hash format + receipt verification + latency."""
from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any
from urllib.request import Request, urlopen

from adapters.base import _PUBLIC_RPC, TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t20"
TEST_NAME = "tx_confirmation"

_TO = "0x0000000000000000000000000000000000000001"
_DEFAULT_TIMEOUT = 30
_RECEIPT_POLL_INTERVAL = 2.0
_RECEIPT_POLL_TIMEOUT = 30.0

# Standard Ethereum tx_hash: 0x + 64 hex chars (32 bytes)
_TX_HASH_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")


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


def _pick_rpc_url(config: dict) -> str:
    params = config.get("test_params", {}).get("t20", {})
    if params.get("rpc_url"):
        return str(params["rpc_url"])
    chain = str(params.get("chain") or config.get("chain") or "ethereum-sepolia")
    if chain in _PUBLIC_RPC:
        return _PUBLIC_RPC[chain]
    return _PUBLIC_RPC.get("ethereum-sepolia", "https://ethereum-sepolia-rpc.publicnode.com")


def _params(config: dict) -> dict[str, Any]:
    return config.get("test_params", {}).get("t20", {})


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    params = _params(config)
    timeout = params.get("timeout", _DEFAULT_TIMEOUT)
    receipt_timeout = params.get("receipt_timeout", _RECEIPT_POLL_TIMEOUT)

    if not adapter.capabilities().get("send_transaction", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的交易确认追踪能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    # --- Phase 1: send transaction ---
    try:
        tx = TxParams(to=_TO, value=0)
        result = await asyncio.wait_for(adapter.send_transaction(tx), timeout=timeout)
    except asyncio.TimeoutError:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"send_transaction 超时 (>{timeout}s)",
            detail={"to": _TO, "value": 0},
            owner="provider",
        )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=f"send_transaction 异常: {exc}",
            detail={"to": _TO, "value": 0, "error": str(exc)[:500]},
            owner="provider",
        )

    send_elapsed = (time.perf_counter() - t0) * 1000
    tx_hash = (result.tx_hash or "").strip()
    valid_hex = bool(_TX_HASH_RE.fullmatch(tx_hash))

    # --- Phase 2: validate hash format ---
    if not tx_hash:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=send_elapsed,
            message="tx_confirmation 失败: tx_hash 缺失",
            detail={"tx_hash": tx_hash, "adapter_status": result.status},
            owner="provider",
        )

    if not valid_hex:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=send_elapsed,
            message=f"tx_confirmation 失败: tx_hash 格式无效 (期望 0x + 64位hex, 实际长度={len(tx_hash)})",
            detail={"tx_hash": tx_hash, "adapter_status": result.status},
            owner="provider",
        )

    # --- Phase 3: poll RPC for receipt (best-effort, does not fail the test) ---
    receipt_status: int | None = None
    receipt_block: int | None = None
    receipt_latency_ms: float | None = None
    receipt_error: str | None = None

    try:
        rpc_url = _pick_rpc_url(config)
        poll_start = time.perf_counter()
        deadline = poll_start + receipt_timeout
        receipt = None
        while time.perf_counter() < deadline:
            raw = _rpc_call(rpc_url, "eth_getTransactionReceipt", [tx_hash])
            if raw is not None:
                receipt = raw
                break
            await asyncio.sleep(_RECEIPT_POLL_INTERVAL)

        if receipt:
            receipt_latency_ms = (time.perf_counter() - poll_start) * 1000
            receipt_status = int(receipt.get("status", "0x0"), 16) if receipt.get("status") else None
            block_hex = receipt.get("blockNumber", "")
            receipt_block = int(block_hex, 16) if block_hex else None
    except Exception as exc:
        receipt_error = str(exc)[:300]

    total_elapsed = (time.perf_counter() - t0) * 1000

    detail = {
        "tx_hash": tx_hash,
        "adapter_status": result.status,
        "adapter_block_number": result.block_number,
        "adapter_gas_used": result.gas_used,
        "receipt_status": receipt_status,
        "receipt_block": receipt_block,
        "receipt_latency_ms": round(receipt_latency_ms, 1) if receipt_latency_ms is not None else None,
        "receipt_error": receipt_error,
        "send_latency_ms": round(send_elapsed, 1),
    }

    # Build descriptive message
    msg_parts = [f"tx_hash 有效 (0x+64hex), 发送耗时 {send_elapsed:.0f}ms"]
    if receipt_status is not None:
        msg_parts.append(f"receipt.status={'success' if receipt_status == 1 else 'revert'}")
    if receipt_latency_ms is not None:
        msg_parts.append(f"receipt 获取耗时 {receipt_latency_ms:.0f}ms")
    if receipt_block is not None:
        msg_parts.append(f"block #{receipt_block}")
    if receipt_error:
        msg_parts.append(f"receipt 查询失败: {receipt_error[:100]}")

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=total_elapsed,
        message="; ".join(msg_parts),
        detail=detail,
        owner="provider",
    )
