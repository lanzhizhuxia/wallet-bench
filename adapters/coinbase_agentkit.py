"""Coinbase AgentKit adapter — CDP Server Wallet (TEE class)."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from adapters.base import (
    SignResult,
    TxParams,
    TxResult,
    WalletAdapter,
    WalletInfo,
)

_ROOT = Path(__file__).resolve().parent.parent


class CoinbaseAgentKitAdapter(WalletAdapter):
    """TEE-class adapter using Coinbase AgentKit's CdpEvmWalletProvider.

    The CDP Server Wallet manages keys server-side.  AgentKit wraps this
    in a Python-friendly SDK with WalletProvider methods (sign_message,
    sign_typed_data, send_transaction, native_transfer, etc.).
    """

    name = "Coinbase AgentKit"
    arch_class = "tee"
    chains = ["base", "ethereum", "polygon", "arbitrum", "optimism"]
    custody_model = "CDP-Server-Wallet"
    signing_modes = ["personal_sign", "eip712", "raw_tx"]
    submission_mode = "provider_submit"

    def __init__(
        self,
        cdp_key_file: str = "cdp_api_key.json",
        network_id: str = "base-sepolia",
        wallet_secret: str = "",
        **kwargs: Any,
    ) -> None:
        key_path = _ROOT / cdp_key_file
        with open(key_path) as f:
            key_data = json.load(f)
        self._api_key_id: str = key_data["id"]
        self._api_key_secret: str = key_data["privateKey"]
        self._wallet_secret: str = wallet_secret or ""
        self._network_id = network_id
        self._wallet_provider = None
        self._address: str | None = None

    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        from coinbase_agentkit import CdpEvmWalletProvider, CdpEvmWalletProviderConfig

        config = CdpEvmWalletProviderConfig(
            api_key_id=self._api_key_id,
            api_key_secret=self._api_key_secret,
            wallet_secret=self._wallet_secret or None,
            network_id=self._network_id,
        )
        self._wallet_provider = CdpEvmWalletProvider(config)
        self._address = self._wallet_provider.get_address()

        # Auto-fund on testnet so tx tests (t19/t20/t23) have balance
        if "sepolia" in self._network_id or "devnet" in self._network_id:
            self._request_testnet_faucet()

    def _request_testnet_faucet(self) -> None:
        """Request testnet ETH from CDP faucet (5x) and wait for confirmation.

        Each faucet call gives ~0.0001 ETH on Base Sepolia. We request 5x
        to ensure enough gas for multiple tx tests (t04/t08/t13/t19/t20/t23).
        """
        try:
            from coinbase_agentkit.action_providers.cdp.cdp_api_action_provider import (
                CdpApiActionProvider,
            )
            import sys

            ap = CdpApiActionProvider()
            ok = 0
            for _ in range(5):
                result = ap.request_faucet_funds(self._wallet_provider, {"asset_id": "eth"})
                if "Error" in result:
                    break
                ok += 1
                time.sleep(1)  # Rate limit between requests
            print(
                f"  [faucet] Funded {self._address} ({ok}x)",
                file=sys.stderr,
            )
            # Wait for balance to appear (faucet tx confirmation)
            for _ in range(20):
                bal = self._wallet_provider.get_balance()
                if bal and int(str(bal)) > 0:
                    break
                time.sleep(1)
        except Exception:
            pass  # Non-critical \u2014 tests degrade gracefully without balance

    async def teardown(self) -> None:
        self._wallet_provider = None

    # -- core operations -----------------------------------------------------

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()
        # Each CdpEvmWalletProvider instance creates/reuses a wallet on init
        # To create a new one, we re-init with a fresh idempotency key
        from coinbase_agentkit import CdpEvmWalletProvider, CdpEvmWalletProviderConfig
        import uuid

        config = CdpEvmWalletProviderConfig(
            api_key_id=self._api_key_id,
            api_key_secret=self._api_key_secret,
            wallet_secret=self._wallet_secret or None,
            network_id=self._network_id,
            idempotency_key=str(uuid.uuid4()),
        )
        wp = CdpEvmWalletProvider(config)
        address = wp.get_address()
        elapsed = (time.perf_counter() - t0) * 1000
        # Keep this as our active wallet
        self._wallet_provider = wp
        self._address = address
        # Auto-fund new wallet on testnet
        if "sepolia" in self._network_id or "devnet" in self._network_id:
            self._request_testnet_faucet()
        return WalletInfo(
            address=address,
            chain=self._network_id,
            meta={"elapsed_ms": elapsed},
        )

    async def sign_message(self, message: str) -> SignResult:
        if not self._wallet_provider:
            await self.setup()
        t0 = time.perf_counter()
        signature = self._wallet_provider.sign_message(message)
        elapsed = (time.perf_counter() - t0) * 1000
        return SignResult(
            signature=signature,
            signer=self._address or "",
            elapsed_ms=elapsed,
        )

    async def sign_typed_data(self, data: dict) -> SignResult:
        if not self._wallet_provider:
            await self.setup()
        t0 = time.perf_counter()
        signature = self._wallet_provider.sign_typed_data(data)
        elapsed = (time.perf_counter() - t0) * 1000
        return SignResult(
            signature=signature,
            signer=self._address or "",
            elapsed_ms=elapsed,
        )

    async def send_transaction(self, tx: TxParams) -> TxResult:
        if not self._wallet_provider:
            await self.setup()
        t0 = time.perf_counter()
        try:
            tx_hash = self._wallet_provider.send_transaction({
                "to": tx.to,
                "value": tx.value if tx.value else 0,
                "data": tx.data or "0x",
            })
            elapsed = (time.perf_counter() - t0) * 1000
            return TxResult(
                tx_hash=tx_hash if isinstance(tx_hash, str) else str(tx_hash),
                status=1,
                elapsed_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            error_msg = str(e)
            # Insufficient funds / revert = business state
            if "insufficient" in error_msg.lower() or "revert" in error_msg.lower():
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
            "policy_enforcement": False,
            "session_delegation": False,
            "estimate_gas": True,
        }

    async def estimate_gas(self, tx: TxParams) -> dict[str, Any]:
        """Use public RPC eth_estimateGas."""
        from adapters.base import eth_estimate_gas_rpc
        chain = f"{self._network_id}" if "sepolia" in self._network_id else "ethereum-sepolia"
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, eth_estimate_gas_rpc, tx.to, tx.value, tx.data,
            self._address, chain,
        )
