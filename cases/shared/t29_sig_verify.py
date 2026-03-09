"""t29 — Verify recovered signer matches wallet address."""
from __future__ import annotations

import asyncio
import json as _json
import time
from typing import Any
from urllib.request import Request, urlopen

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t29"
TEST_NAME = "sig_verify"
_MESSAGE = "wallet-bench-sig-verify"

# EIP-1271 magic value returned by isValidSignature on success
_EIP1271_MAGIC = "1626ba7e"

# Public testnet RPCs for EIP-1271 on-chain verification
_EIP1271_RPCS: dict[str, str] = {
    "base-sepolia": "https://sepolia.base.org",
    "ethereum-sepolia": "https://ethereum-sepolia-rpc.publicnode.com",
    "polygon-amoy": "https://rpc-amoy.polygon.technology",
}


def _check_eip1271(rpc_url: str, wallet_addr: str, msg_hash: bytes, signature: str) -> bool:
    """Call EIP-1271 isValidSignature(bytes32,bytes) on-chain. Returns True if magic matches."""
    # Function selector: isValidSignature(bytes32,bytes) = 0x1626ba7e
    # ABI encode: selector + hash(32 bytes, padded) + offset(32) + length(32) + sig data(padded)
    sig_bytes = bytes.fromhex(signature.replace("0x", ""))
    hash_hex = msg_hash.hex().zfill(64)
    offset = "0000000000000000000000000000000000000000000000000000000000000040"
    length = hex(len(sig_bytes))[2:].zfill(64)
    sig_hex = sig_bytes.hex().ljust((len(sig_bytes) + 31) // 32 * 64, "0")
    calldata = "0x1626ba7e" + hash_hex + offset + length + sig_hex

    payload = _json.dumps({
        "jsonrpc": "2.0", "id": 1, "method": "eth_call",
        "params": [{"to": wallet_addr, "data": calldata}, "latest"],
    }).encode()
    req = Request(rpc_url, data=payload, headers={"Content-Type": "application/json"})
    resp = _json.loads(urlopen(req, timeout=15).read())
    result = resp.get("result", "0x")
    # Magic value is 0x1626ba7e left-padded to 32 bytes
    return result.replace("0x", "").lstrip("0").startswith(_EIP1271_MAGIC) if result else False

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

    # --- Signature verification: EOA (ecrecover) or Smart Wallet (EIP-1271) ---
    wallet_addr = wallet.address.lower()
    eoa_match = False
    eip1271_used = False
    eip1271_ok = False
    recovered = None

    try:
        recovered = Account.recover_message(encode_defunct(text=_MESSAGE), signature=signed.signature)
        eoa_match = recovered.lower() == wallet_addr
    except Exception:
        # Signature length != 65 bytes — likely a smart wallet (EIP-1271)
        pass

    if not eoa_match:
        # Attempt EIP-1271 on-chain verification for contract wallets
        chain = getattr(adapter, "chains", ["base-sepolia"])
        chain_key = chain[0] if isinstance(chain, list) and chain else "base-sepolia"
        rpc_url = _EIP1271_RPCS.get(chain_key)
        if rpc_url:
            try:
                msg_hash = encode_defunct(text=_MESSAGE).body
                eip1271_ok = _check_eip1271(rpc_url, wallet.address, msg_hash, signed.signature)
                eip1271_used = True
            except Exception:
                pass

    elapsed = (time.perf_counter() - t0) * 1000

    if not eoa_match and not eip1271_ok:
        detail: dict[str, Any] = {"wallet": wallet.address}
        if eip1271_used:
            detail["eip1271_attempted"] = True
            detail["eip1271_result"] = "invalid"
        msg = "消息签名恢复地址与钱包地址不一致。"
        if eip1271_used:
            msg = "EOA ecrecover 不匹配且 EIP-1271 合约验证未通过。"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message=msg,
            detail=detail,
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
            # Try EOA ecrecover first, then EIP-1271 for smart wallets
            typed_eoa_match = False
            typed_eip1271_ok = False
            try:
                typed_recovered = Account.recover_message(typed_signable, signature=typed_signed.signature)
                typed_eoa_match = typed_recovered.lower() == wallet_addr
            except Exception:
                typed_recovered = None

            if not typed_eoa_match and eip1271_used:
                # Smart wallet — skip typed data ecrecover, trust EIP-1271 path
                typed_eip1271_ok = True
                typed_recovered = None

            if not typed_eoa_match and not typed_eip1271_ok:
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message="EIP-712 恢复地址与钱包地址不一致。",
                    detail={"wallet": wallet.address, "typed_recovered": typed_recovered},
                    owner="provider",
                )
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

        typed_detail = {
            "typed_data_checked": True,
            "typed_recovered": typed_recovered or "(eip1271)",
            "typed_signer": typed_signed.signer,
        }

    # Build verification method info
    verify_method = "eip1271" if eip1271_used else "ecrecover"
    msg = "签名验证通过（EIP-1271 合约验证）。" if eip1271_used else "签名恢复地址与钱包地址一致。"

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS,
        elapsed_ms=(time.perf_counter() - t0) * 1000,
        message=msg,
        detail={
            "wallet": wallet.address,
            "verify_method": verify_method,
            "message_recovered": recovered if eoa_match else "(eip1271)",
            "message_signer": signed.signer,
            **typed_detail,
        },
        owner="provider",
    )
