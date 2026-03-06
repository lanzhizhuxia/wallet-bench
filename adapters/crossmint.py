"""Crossmint Smart Wallets adapter — REST API (staging)."""

from __future__ import annotations

import asyncio
import json
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from adapters.base import (
    SignResult,
    TxParams,
    TxResult,
    WalletAdapter,
    WalletInfo,
)

_API_BASE = "https://staging.crossmint.com/api/2025-06-09"
_POLL_INTERVAL = 2.0
_POLL_TIMEOUT = 60.0
_DEFAULT_CHAIN = "base-sepolia"


class CrossmintAdapter(WalletAdapter):
    """Intent-class adapter for Crossmint Smart Wallets (staging).

    Uses API version 2025-06-09 with smart wallets configured to
    ``external-wallet`` admin signer. Signature/transaction requests may enter
    ``awaiting-approval`` and require EOA EIP-191 approval before completion.
    """

    name = "Crossmint Smart Wallets"
    arch_class = "intent"
    chains = ["base-sepolia", "ethereum-sepolia", "polygon-amoy",
              "arbitrum-sepolia", "optimism-sepolia", "solana"]
    custody_model = "External-Wallet"
    signing_modes = ["personal_sign", "eip712", "raw_tx"]
    submission_mode = "provider_submit"

    def __init__(
        self,
        api_key: str,
        chain: str = _DEFAULT_CHAIN,
        eoa_private_key: str = "",
        **kwargs,
    ) -> None:
        from eth_account import Account

        self._api_key = api_key
        self._chain = chain
        self._wallet_address: str | None = None
        self._linked_user = f"email:wallet-bench-{int(time.time())}@example.com"
        self._eoa_private_key = eoa_private_key or kwargs.get("eoa_private_key", "")
        if not self._eoa_private_key:
            raise ValueError(
                "Crossmint adapter requires 'eoa_private_key' in config.yaml "
                "or WALLET_BENCH_PRIVATE_KEY in .env"
            )
        self._eoa_address = Account.from_key(self._eoa_private_key).address

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{_API_BASE}{path}"
        data = json.dumps(body).encode() if body else None
        req = Request(url, data=data, method=method)
        req.add_header("X-API-KEY", self._api_key)
        req.add_header("Content-Type", "application/json")
        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            error_body = e.read().decode()
            raise RuntimeError(f"Crossmint API {e.code}: {error_body}") from e

    async def _async_request(self, method: str, path: str, body: dict | None = None) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._request, method, path, body)

    async def _poll_until_done(self, path: str) -> dict:
        deadline = time.monotonic() + _POLL_TIMEOUT
        while time.monotonic() < deadline:
            result = await self._async_request("GET", path)
            status = result.get("status", "")
            if status not in ("pending", "awaiting-approval"):
                return result
            await asyncio.sleep(_POLL_INTERVAL)
        raise TimeoutError(f"Crossmint operation timed out after {_POLL_TIMEOUT}s")

    async def _approve_signature(self, sig_id: str, initial_resp: dict) -> dict:
        from eth_account import Account
        from eth_account.messages import encode_defunct

        pending = initial_resp.get("approvals", {}).get("pending", [])
        if not pending:
            return await self._poll_until_done(f"/wallets/{self._wallet_address}/signatures/{sig_id}")

        pending_hash = pending[0].get("message", "")
        if not pending_hash:
            return await self._poll_until_done(f"/wallets/{self._wallet_address}/signatures/{sig_id}")

        account = Account.from_key(self._eoa_private_key)
        msg = encode_defunct(hexstr=pending_hash)
        signed = account.sign_message(msg)
        signature = "0x" + signed.signature.hex()

        result = await self._async_request(
            "POST",
            f"/wallets/{self._wallet_address}/signatures/{sig_id}/approvals",
            {"approvals": [{"signer": f"external-wallet:{self._eoa_address}", "signature": signature}]},
        )

        if result.get("status") not in ("success", "failed"):
            return await self._poll_until_done(f"/wallets/{self._wallet_address}/signatures/{sig_id}")
        return result

    async def _approve_transaction(self, tx_id: str, initial_resp: dict) -> dict:
        from eth_account import Account
        from eth_account.messages import encode_defunct

        pending = initial_resp.get("approvals", {}).get("pending", [])
        if not pending:
            return await self._poll_until_done(f"/wallets/{self._wallet_address}/transactions/{tx_id}")

        pending_hash = pending[0].get("message", "")
        if not pending_hash:
            return await self._poll_until_done(f"/wallets/{self._wallet_address}/transactions/{tx_id}")

        account = Account.from_key(self._eoa_private_key)
        msg = encode_defunct(hexstr=pending_hash)
        signed = account.sign_message(msg)
        signature = "0x" + signed.signature.hex()

        result = await self._async_request(
            "POST",
            f"/wallets/{self._wallet_address}/transactions/{tx_id}/approvals",
            {"approvals": [{"signer": f"external-wallet:{self._eoa_address}", "signature": signature}]},
        )

        if result.get("status") not in ("success", "failed"):
            return await self._poll_until_done(f"/wallets/{self._wallet_address}/transactions/{tx_id}")
        return result

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()
        resp = await self._async_request("POST", "/wallets", {
            "chainType": "evm",
            "type": "smart",
            "config": {
                "adminSigner": {
                    "type": "external-wallet",
                    "address": self._eoa_address,
                }
            },
            "owner": self._linked_user,
        })
        elapsed = (time.perf_counter() - t0) * 1000
        address = resp.get("address", "")
        self._wallet_address = address
        return WalletInfo(
            address=address,
            chain=self._chain,
            meta={"elapsed_ms": elapsed, "raw": resp},
        )

    async def sign_message(self, message: str) -> SignResult:
        if not self._wallet_address:
            await self.create_wallet()
        t0 = time.perf_counter()
        resp = await self._async_request(
            "POST",
            f"/wallets/{self._wallet_address}/signatures",
            {
                "type": "message",
                "params": {"message": message, "chain": self._chain},
            },
        )
        sig_id = resp.get("id", "")
        result = await self._approve_signature(sig_id, resp)
        elapsed = (time.perf_counter() - t0) * 1000
        output_sig = result.get("outputSignature", "") or ""
        return SignResult(
            signature=output_sig,
            signer=self._wallet_address or "",
            elapsed_ms=elapsed,
            meta={"raw": result},
        )

    async def sign_typed_data(self, data: dict) -> SignResult:
        if not self._wallet_address:
            await self.create_wallet()
        t0 = time.perf_counter()
        resp = await self._async_request(
            "POST",
            f"/wallets/{self._wallet_address}/signatures",
            {
                "type": "typed-data",
                "params": {"typedData": data, "chain": self._chain},
            },
        )
        sig_id = resp.get("id", "")
        result = await self._approve_signature(sig_id, resp)
        elapsed = (time.perf_counter() - t0) * 1000
        output_sig = result.get("outputSignature", "") or ""
        return SignResult(
            signature=output_sig,
            signer=self._wallet_address or "",
            elapsed_ms=elapsed,
            meta={"raw": result},
        )

    async def send_transaction(self, tx: TxParams) -> TxResult:
        if not self._wallet_address:
            await self.create_wallet()
        t0 = time.perf_counter()
        value_wei = str(tx.value) if tx.value else "0"
        try:
            resp = await self._async_request(
                "POST",
                f"/wallets/{self._wallet_address}/transactions",
                {
                    "params": {
                        "calls": [{
                            "to": tx.to,
                            "value": value_wei,
                            "data": tx.data or "0x",
                        }],
                        "chain": self._chain,
                    },
                },
            )
        except RuntimeError as e:
            error_msg = str(e)
            elapsed = (time.perf_counter() - t0) * 1000
            if "execution_reverted" in error_msg or "422" in error_msg:
                return TxResult(
                    tx_hash="",
                    status=0,
                    elapsed_ms=elapsed,
                    meta={"error": error_msg, "revert": True},
                )
            raise

        tx_id = resp.get("id", "")
        result = await self._approve_transaction(tx_id, resp)
        elapsed = (time.perf_counter() - t0) * 1000
        tx_hash = result.get("onChain", {}).get("txId", "") or result.get("onChain", {}).get("transactionHash", "")
        status_str = result.get("status", "")
        return TxResult(
            tx_hash=tx_hash,
            status=1 if status_str == "success" else 0,
            elapsed_ms=elapsed,
            meta={"raw": result},
        )

    def capabilities(self) -> dict[str, bool]:
        return {
            "create_wallet": True,
            "sign_message": True,
            "sign_typed_data": True,
            "send_transaction": True,
            "multi_chain": True,
            "policy_enforcement": False,
            "session_delegation": False,
            "estimate_gas": True,
        }

    async def estimate_gas(self, tx: TxParams) -> dict[str, Any]:
        """Use public RPC eth_estimateGas."""
        from adapters.base import eth_estimate_gas_rpc
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, eth_estimate_gas_rpc, tx.to, tx.value, tx.data,
            self._wallet_address or self._eoa_address, self._chain,
        )
