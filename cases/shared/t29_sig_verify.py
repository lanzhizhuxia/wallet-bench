"""t29 — Verify recovered signer matches wallet address."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t29"
TEST_NAME = "sig_verify"
_MESSAGE = "wallet-bench-sig-verify"

_SAMPLE_TYPED_DATA: dict[str, Any] = {
    "types": {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
        "Verify": [
            {"name": "message", "type": "string"},
            {"name": "nonce", "type": "uint256"},
        ],
    },
    "primaryType": "Verify",
    "domain": {
        "name": "wallet-bench",
        "version": "1",
        "chainId": 97,
        "verifyingContract": "0x0000000000000000000000000000000000000001",
    },
    "message": {"message": "wallet-bench-typed-verify", "nonce": 1},
}


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("sign_message", False):
        if "sign_message" in adapter.provider_unsupported():
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.UNSUPPORTED,
                elapsed_ms=0.0,
                message="该供应商不支持消息签名能力。",
                owner="provider",
            )
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="本轮基准未接入该供应商的消息签名能力，无法验证。",
            owner="benchmark",
        )

    try:
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except Exception:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="缺少 eth_account，无法执行签名恢复验证。",
            owner="benchmark",
        )

    params = config.get("test_params", {}).get(TEST_ID, {})
    timeout_s = float(params.get("timeout_s", 60))

    t0 = time.perf_counter()
    try:
        wallet = await asyncio.wait_for(adapter.create_wallet(), timeout=timeout_s)
        signed = await asyncio.wait_for(adapter.sign_message(_MESSAGE), timeout=timeout_s)
        recovered = Account.recover_message(encode_defunct(text=_MESSAGE), signature=signed.signature)
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
    wallet_addr = wallet.address.lower()
    recovered_addr = recovered.lower()
    if recovered_addr != wallet_addr:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="消息签名恢复地址与钱包地址不一致。",
            detail={"wallet": wallet.address, "recovered": recovered},
            owner="provider",
        )

    typed_detail: dict[str, Any] = {"typed_data_checked": False}
    if adapter.capabilities().get("sign_typed_data", False):
        try:
            from eth_account.messages import encode_typed_data
        except Exception:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.INCONCLUSIVE,
                elapsed_ms=elapsed,
                message="sign_typed_data 可用但当前环境无法编码 EIP-712 数据。",
                detail={"wallet": wallet.address},
                owner="benchmark",
            )

        try:
            typed_signed = await asyncio.wait_for(adapter.sign_typed_data(_SAMPLE_TYPED_DATA), timeout=timeout_s)
            typed_signable = encode_typed_data(full_message=_SAMPLE_TYPED_DATA)
            typed_recovered = Account.recover_message(typed_signable, signature=typed_signed.signature)
        except Exception as exc:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message=f"EIP-712 签名验证失败: {exc}",
                detail={"wallet": wallet.address},
                owner="provider",
            )

        if typed_recovered.lower() != wallet_addr:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="EIP-712 恢复地址与钱包地址不一致。",
                detail={"wallet": wallet.address, "typed_recovered": typed_recovered},
                owner="provider",
            )

        typed_detail = {
            "typed_data_checked": True,
            "typed_recovered": typed_recovered,
            "typed_signer": typed_signed.signer,
        }

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=(time.perf_counter() - t0) * 1000,
        message="签名恢复地址与钱包地址一致。",
        detail={
            "wallet": wallet.address,
            "message_recovered": recovered,
            "message_signer": signed.signer,
            **typed_detail,
        },
        owner="provider",
    )
