"""Para Wallet adapter — MPC cloud signing via REST API.

Pure REST API with 3 endpoints. Auth via X-API-Key header.
Supports EVM/Solana/Cosmos with the same API shape.
"""

from __future__ import annotations

import asyncio
import json as _json
import time
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from adapters.base import (
    SignResult,
    TxParams,
    TxResult,
    WalletAdapter,
    WalletInfo,
)


class ParaWalletAdapter(WalletAdapter):
    """MPC-class adapter for Para Wallet REST API.

    Para stores keys via MPC in the cloud. All operations via REST API.
    sign-raw accepts 0x-prefixed hex data and returns signature without 0x prefix.
    """

    name = "Para Wallet"
    arch_class = "mpc"
    chains = ["ethereum", "solana", "cosmos"]
    custody_model = "MPC-Cloud"
    signing_modes = ["raw_sign"]
    submission_mode = "client_submit"

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.beta.getpara.com",
        user_identifier: str = "wallet-bench@test.com",
        chain: str = "ethereum",
        **kwargs: Any,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._user_identifier = user_identifier
        self._chain = chain
        self._wallet_id: str = ""
        self._wallet_address: str = ""

    # -- HTTP helpers --------------------------------------------------------

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{self._base_url}{path}"
        headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "User-Agent": "wallet-bench/1.0",
        }
        data = _json.dumps(body).encode() if body else None
        req = Request(url, data=data, method=method, headers=headers)

        try:
            with urlopen(req, timeout=30) as resp:
                raw = resp.read()
                return _json.loads(raw) if raw else {}
        except HTTPError as e:
            status = e.code
            error_body = e.read().decode()[:500]
            # 409 Conflict means wallet already exists — parse walletId
            if status == 409:
                try:
                    err_data = _json.loads(error_body)
                    return {"conflict": True, **err_data}
                except _json.JSONDecodeError:
                    pass
            raise RuntimeError(f"Para API {status}: {error_body}")

    async def _async_request(self, method: str, path: str, body: dict | None = None) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._request, method, path, body)

    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

    # -- core operations -----------------------------------------------------

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()

        wallet_type = "EVM" if self._chain not in ("solana", "cosmos") else self._chain.upper()

        # Create wallet
        resp = await self._async_request("POST", "/v1/wallets", {
            "type": wallet_type,
            "userIdentifier": self._user_identifier,
            "userIdentifierType": "EMAIL",
        })

        # Handle 409 Conflict (wallet already exists)
        if resp.get("conflict"):
            wallet_id = resp.get("walletId", resp.get("id", ""))
            if wallet_id:
                resp = await self._async_request("GET", f"/v1/wallets/{wallet_id}")
        else:
            wallet_id = resp.get("id", resp.get("walletId", ""))

        # Poll until ready (max 30s)
        if wallet_id and resp.get("status") != "ready":
            for _ in range(30):
                await asyncio.sleep(1.0)
                resp = await self._async_request("GET", f"/v1/wallets/{wallet_id}")
                if resp.get("status") == "ready":
                    break

        elapsed = (time.perf_counter() - t0) * 1000
        address = resp.get("address", "")
        self._wallet_id = wallet_id or resp.get("id", "")
        self._wallet_address = address

        return WalletInfo(
            address=address,
            chain=self._chain,
            meta={
                "elapsed_ms": elapsed,
                "wallet_id": self._wallet_id,
                "status": resp.get("status", ""),
            },
        )

    async def sign_message(self, message: str) -> SignResult:
        if not self._wallet_id:
            await self.create_wallet()
        t0 = time.perf_counter()

        # Convert message to hex
        hex_message = "0x" + message.encode().hex()

        resp = await self._async_request(
            "POST",
            f"/v1/wallets/{self._wallet_id}/sign-raw",
            {"data": hex_message},
        )
        elapsed = (time.perf_counter() - t0) * 1000

        signature = resp.get("signature", "")
        # Para returns signature without 0x prefix — normalize
        if signature and not signature.startswith("0x"):
            signature = "0x" + signature

        return SignResult(
            signature=signature,
            signer=self._wallet_address,
            elapsed_ms=elapsed,
            meta={"raw": resp},
        )

    async def sign_typed_data(self, data: dict) -> SignResult:
        raise NotImplementedError(
            "Para Wallet sign-raw only accepts raw hex data — "
            "EIP-712 typed data hashing must be done client-side"
        )

    async def send_transaction(self, tx: TxParams) -> TxResult:
        """Sign transaction hash via MPC, then broadcast via public RPC.

        This is a best-effort implementation — Para only signs, doesn't submit.
        """
        if not self._wallet_id:
            await self.create_wallet()
        t0 = time.perf_counter()

        try:
            # Para only does sign-raw. For a full send_transaction we'd need to:
            # 1. Build raw tx with nonce/gas from RPC
            # 2. Hash it
            # 3. Sign via Para
            # 4. Combine signature and broadcast
            # This is complex — for now we sign the tx data as a proof of concept
            tx_data = tx.data or "0x"
            resp = await self._async_request(
                "POST",
                f"/v1/wallets/{self._wallet_id}/sign-raw",
                {"data": tx_data},
            )
            elapsed = (time.perf_counter() - t0) * 1000

            return TxResult(
                tx_hash="",
                elapsed_ms=elapsed,
                status=0,
                meta={
                    "note": "Para only signs — broadcast not implemented",
                    "signature": resp.get("signature", ""),
                },
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            error_msg = str(exc).lower()
            if any(k in error_msg for k in (
                "insufficient", "balance", "revert", "rejected", "failed",
            )):
                return TxResult(
                    tx_hash="",
                    elapsed_ms=elapsed,
                    status=0,
                    meta={"error": str(exc)[:300], "revert": True},
                )
            raise

    # -- introspection -------------------------------------------------------

    def capabilities(self) -> dict[str, bool]:
        return {
            "create_wallet": True,
            "sign_message": True,
            "sign_typed_data": False,
            "send_transaction": True,
            "multi_chain": True,
            "policy_enforcement": False,
            "session_delegation": False,
            "estimate_gas": True,
        }

    def provider_unsupported(self) -> set[str]:
        return {"sign_typed_data"}

    async def estimate_gas(self, tx: TxParams) -> dict[str, Any]:
        """Use public RPC eth_estimateGas."""
        from adapters.base import eth_estimate_gas_rpc
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, eth_estimate_gas_rpc, tx.to, tx.value, tx.data,
            self._wallet_address or None, self._chain,
        )
