"""t08 — Concurrent operations (parallel create_wallet / send_transaction)."""

from __future__ import annotations

import asyncio
import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t08"
TEST_NAME = "concurrent_ops"

_BURN_ADDRESS = "0x0000000000000000000000000000000000000001"
_TINY_VALUE_WEI = 10**14


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    cap = adapter.capabilities()
    if not cap.get("create_wallet", False) or not cap.get("sign_message", False):
        # If sign_message is provider-unsupported, concurrent ops can't be tested
        if "sign_message" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                message="该供应商不支持消息签名，无法执行并发混合负载测试。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的并发操作能力（需同时支持钱包创建与消息签名），无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    include_send = cap.get("send_transaction", False)

    op_names: list[str]
    if include_send:
        tx = TxParams(to=_BURN_ADDRESS, value=_TINY_VALUE_WEI)
        op_names = [
            "create_wallet",
            "create_wallet",
            "sign_message",
            "sign_message",
            "send_transaction",
        ]
    else:
        op_names = [
            "create_wallet",
            "create_wallet",
            "sign_message",
            "sign_message",
            "sign_message",
        ]

    t0 = time.perf_counter()
    try:
        if include_send:
            results = await asyncio.gather(
                adapter.create_wallet(),
                adapter.create_wallet(),
                adapter.sign_message("concurrent test 1"),
                adapter.sign_message("concurrent test 2"),
                adapter.send_transaction(tx),
                return_exceptions=True,
            )
        else:
            results = await asyncio.gather(
                adapter.create_wallet(),
                adapter.create_wallet(),
                adapter.sign_message("concurrent test 1"),
                adapter.sign_message("concurrent test 2"),
                adapter.sign_message("concurrent test 3"),
                return_exceptions=True,
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

    addresses: list[str] = []
    signatures: list[str] = []
    tx_hashes: list[str] = []
    errors: list[str] = []

    for op, result in zip(op_names, results):
        if isinstance(result, Exception):
            errors.append(f"{op}: {result}")
            continue

        if op == "create_wallet":
            address = str(getattr(result, "address", "")).strip()
            if not address:
                errors.append("create_wallet: empty address")
                continue
            addresses.append(address)
        elif op == "sign_message":
            signature = str(getattr(result, "signature", "")).strip()
            if not signature:
                errors.append("sign_message: empty signature")
                continue
            signatures.append(signature)
        elif op == "send_transaction":
            tx_hash = str(getattr(result, "tx_hash", "")).strip()
            if not tx_hash:
                errors.append("send_transaction: empty tx_hash")
                continue
            tx_hashes.append(tx_hash)

    if len(set(addresses)) != len(addresses):
        errors.append("create_wallet: duplicate addresses in concurrent results")

    if errors:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=f"并发混合负载失败: {len(errors)} 个问题",
            detail={
                "errors": errors,
                "addresses": addresses,
                "signatures": signatures,
                "tx_hashes": tx_hashes,
            },
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=elapsed,
        message="并发混合负载执行成功",
        detail={
            "addresses": addresses,
            "signatures": signatures,
            "tx_hashes": tx_hashes,
        },
    )
