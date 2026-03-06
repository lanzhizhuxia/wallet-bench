"""Privy Server Wallets adapter — REST API (TEE class)."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from typing import Any

import requests as _requests

from adapters.base import (
    SignResult,
    TxParams,
    TxResult,
    WalletAdapter,
    WalletInfo,
)

_API_BASE = "https://auth.privy.io/api/v1"


class PrivyAdapter(WalletAdapter):
    """TEE-class adapter for Privy Server Wallets.

    Privy stores keys in TEE (AWS Nitro Enclave) with key sharding.
    All operations via REST API with Basic auth (app_id:app_secret).
    Wallets are created per-app, signing is synchronous.
    """

    name = "Privy Server Wallets"
    arch_class = "tee"
    chains = ["ethereum", "base", "polygon", "arbitrum", "optimism", "solana"]
    custody_model = "TEE+Shard"
    signing_modes = ["personal_sign", "eip712", "raw_tx"]
    submission_mode = "provider_submit"

    def __init__(
        self,
        app_id: str = "",
        app_secret: str = "",
        chain: str = "ethereum-sepolia",
        wallet_id: str = "",
        **kwargs: Any,
    ) -> None:
        self._app_id = app_id
        self._app_secret = app_secret
        self._chain = chain
        self._wallet_id: str | None = wallet_id or None
        self._initial_wallet_id: str | None = wallet_id or None  # Track pre-configured wallet
        self._wallet_address: str | None = None
        # Chain ID mapping for Privy RPC calls
        self._chain_ids = {
            "ethereum-sepolia": 11155111,
            "base-sepolia": 84532,
            "polygon-amoy": 80002,
            "arbitrum-sepolia": 421614,
            "optimism-sepolia": 11155420,
        }

    # -- HTTP helpers --------------------------------------------------------

    def _auth_header(self) -> str:
        """Basic auth header: base64(app_id:app_secret)."""
        cred = f"{self._app_id}:{self._app_secret}"
        return "Basic " + base64.b64encode(cred.encode()).decode()

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{_API_BASE}{path}"
        headers = {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
            "privy-app-id": self._app_id,
            "User-Agent": "wallet-bench/1.0",
        }
        resp = _requests.request(
            method, url, headers=headers,
            json=body if body else None,
            timeout=30,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Privy API {resp.status_code}: {resp.text}")
        return resp.json() if resp.text else {}

    async def _async_request(self, method: str, path: str, body: dict | None = None) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._request, method, path, body)

    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        # If wallet_id was provided in config, resolve its address
        if self._wallet_id and not self._wallet_address:
            resp = await self._async_request(
                "GET", f"/wallets/{self._wallet_id}"
            )
            self._wallet_address = resp.get("address", "")

    async def teardown(self) -> None:
        pass

    # -- core operations -----------------------------------------------------

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()
        chain_type = "ethereum"  # EVM wallets
        resp = await self._async_request("POST", "/wallets", {
            "chain_type": chain_type,
        })
        elapsed = (time.perf_counter() - t0) * 1000
        new_id = resp.get("id", "")
        new_address = resp.get("address", "")
        # Only adopt the new wallet if no pre-funded wallet is configured.
        # When wallet_id is set in config, we keep using that funded wallet
        # for tx tests; create_wallet still proves the API works.
        if not self._initial_wallet_id:
            self._wallet_id = new_id
            self._wallet_address = new_address
        return WalletInfo(
            address=new_address,
            chain=self._chain,
            meta={
                "elapsed_ms": elapsed,
                "wallet_id": new_id,
                "chain_type": chain_type,
            },
        )

    async def sign_message(self, message: str) -> SignResult:
        if not self._wallet_id:
            await self.create_wallet()
        t0 = time.perf_counter()
        resp = await self._async_request(
            "POST",
            f"/wallets/{self._wallet_id}/rpc",
            {
                "method": "personal_sign",
                "params": {
                    "message": message,
                    "encoding": "utf-8",
                },
            },
        )
        elapsed = (time.perf_counter() - t0) * 1000
        signature = resp.get("data", {}).get("signature", "")
        return SignResult(
            signature=signature,
            signer=self._wallet_address or "",
            elapsed_ms=elapsed,
            meta={"raw": resp},
        )

    async def sign_typed_data(self, data: dict) -> SignResult:
        if not self._wallet_id:
            await self.create_wallet()
        t0 = time.perf_counter()
        # Privy expects snake_case keys in typed_data, not camelCase
        privy_data = {
            "domain": data.get("domain", {}),
            "types": data.get("types", {}),
            "primary_type": data.get("primaryType", data.get("primary_type", "")),
            "message": data.get("message", {}),
        }
        resp = await self._async_request(
            "POST",
            f"/wallets/{self._wallet_id}/rpc",
            {
                "method": "eth_signTypedData_v4",
                "params": {
                    "typed_data": privy_data,
                },
            },
        )
        elapsed = (time.perf_counter() - t0) * 1000
        signature = resp.get("data", {}).get("signature", "")
        return SignResult(
            signature=signature,
            signer=self._wallet_address or "",
            elapsed_ms=elapsed,
            meta={"raw": resp},
        )

    async def send_transaction(self, tx: TxParams) -> TxResult:
        if not self._wallet_id:
            await self.create_wallet()
        t0 = time.perf_counter()
        chain_id = self._chain_ids.get(self._chain, 11155111)
        try:
            resp = await self._async_request(
                "POST",
                f"/wallets/{self._wallet_id}/rpc",
                {
                    "method": "eth_sendTransaction",
                    "caip2": f"eip155:{chain_id}",
                    "params": {
                        "transaction": {
                            "to": tx.to,
                            "value": hex(tx.value) if tx.value else "0x0",
                            "data": tx.data or "0x",
                        },
                    },
                },
            )
            elapsed = (time.perf_counter() - t0) * 1000
            tx_hash = resp.get("data", {}).get("hash", "") or resp.get("data", {}).get("transaction_hash", "")
            return TxResult(
                tx_hash=tx_hash,
                status=1,
                elapsed_ms=elapsed,
                meta={"raw": resp},
            )
        except RuntimeError as e:
            elapsed = (time.perf_counter() - t0) * 1000
            error_msg = str(e)
            if "insufficient" in error_msg.lower() or "revert" in error_msg.lower() or "funds" in error_msg.lower():
                return TxResult(
                    tx_hash="",
                    status=0,
                    elapsed_ms=elapsed,
                    meta={"error": error_msg, "revert": True},
                )
            raise

    # -- introspection -------------------------------------------------------

    def capabilities(self) -> dict[str, bool]:
        return {
            "create_wallet": True,
            "sign_message": True,
            "sign_typed_data": True,
            "send_transaction": True,
            "multi_chain": True,
            # policy_enforcement: True — Privy has policy engine (enterprise feature, see evaluation notes)
            "session_delegation": False,
            "estimate_gas": True,
        }

    async def estimate_gas(self, tx: TxParams) -> dict[str, Any]:
        """Use public RPC eth_estimateGas (Privy RPC doesn't expose this method)."""
        from adapters.base import eth_estimate_gas_rpc
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, eth_estimate_gas_rpc, tx.to, tx.value, tx.data,
            self._wallet_address, self._chain,
        )
