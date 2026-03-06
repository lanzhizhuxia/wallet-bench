"""Minara AI adapter — talks to minara CLI via subprocess.

Minara is a custodial agent wallet (keys held server-side).
No signing primitives are exposed — only high-level operations
(transfer, swap, balance). The adapter maps what's available
to the WalletAdapter interface.
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from adapters.base import (
    SignResult,
    TxParams,
    TxResult,
    WalletAdapter,
    WalletInfo,
)


class MinaraAdapter(WalletAdapter):
    """MPC+AA-class adapter for Minara AI CLI.

    Uses ``minara`` CLI.  Minara manages keys server-side (custodial).
    No message signing or typed-data signing is available.
    """

    name = "Minara AI"
    arch_class = "mpc_aa"
    chains = [
        "ethereum", "base", "arbitrum", "optimism",
        "polygon", "avalanche", "bnb", "berachain",
        "solana",
    ]
    custody_model = "Custodial-Smart-Wallet"
    signing_modes = ["raw_tx"]
    submission_mode = "provider_submit"

    def __init__(self, chain: str = "base", **kwargs: Any) -> None:
        self._chain = chain
        self._evm_address: str = ""
        self._sol_address: str = ""

    # -- helpers -------------------------------------------------------------

    async def _run_minara(self, *args: str, timeout: float = 30) -> str:
        """Run ``minara <args>`` and return stdout as text."""
        cmd = ["minara", *args]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,  # prevent interactive prompts
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"minara command timed out: {' '.join(cmd)}")

        out = stdout.decode().strip()
        err = stderr.decode().strip()

        if proc.returncode != 0:
            raise RuntimeError(f"minara exited {proc.returncode}: {(err or out)[:300]}")

        return out

    def _parse_addresses(self, text: str) -> dict[str, str]:
        """Extract wallet addresses from account/deposit output."""
        addresses: dict[str, str] = {}
        # Match patterns like "spot-evm : 0x..." or "Address : 0x..."
        for line in text.split("\n"):
            line = line.strip()
            # EVM address
            evm_match = re.search(r"(0x[0-9a-fA-F]{40})", line)
            if evm_match:
                addr = evm_match.group(1)
                if "spot-evm" in line.lower() or "abstraction-evm" in line.lower():
                    addresses["evm"] = addr
                elif "evm" not in addresses:
                    addresses["evm"] = addr
            # Solana address (base58, 32-44 chars)
            sol_match = re.search(r"(?:spot-solana|abstraction-solana|Solana)\s*[:\s]+([1-9A-HJ-NP-Za-km-z]{32,44})", line)
            if sol_match:
                if "solana" not in addresses:
                    addresses["solana"] = sol_match.group(1)
        return addresses

    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        """Verify CLI is logged in and extract wallet addresses."""
        out = await self._run_minara("account")
        addresses = self._parse_addresses(out)
        self._evm_address = addresses.get("evm", "")
        self._sol_address = addresses.get("solana", "")

        if not self._evm_address and not self._sol_address:
            raise RuntimeError(
                "Could not extract wallet addresses from `minara account`. "
                "Are you logged in? Run: minara login"
            )

    async def teardown(self) -> None:
        pass

    # -- core operations -----------------------------------------------------

    async def create_wallet(self) -> WalletInfo:
        """Return the existing custodial wallet address.

        Minara wallets are created at registration time — there's no
        create_wallet command.  We return the existing address.
        """
        t0 = time.perf_counter()
        out = await self._run_minara("account")
        elapsed = (time.perf_counter() - t0) * 1000

        addresses = self._parse_addresses(out)
        if self._chain == "solana":
            address = addresses.get("solana", self._sol_address)
        else:
            address = addresses.get("evm", self._evm_address)

        return WalletInfo(
            address=address,
            chain=self._chain,
            meta={"elapsed_ms": elapsed, "custodial": True},
        )

    async def sign_message(self, message: str) -> SignResult:
        raise NotImplementedError("Minara does not expose message signing")

    async def sign_typed_data(self, data: dict) -> SignResult:
        raise NotImplementedError("Minara does not expose typed data signing")

    async def send_transaction(self, tx: TxParams) -> TxResult:
        """Attempt a token transfer via Minara CLI.

        Uses the native token (ETH on EVM chains).  Will likely fail due to
        zero balance, but we verify the error is clean.
        """
        t0 = time.perf_counter()
        from decimal import Decimal
        amount_ether = str(Decimal(tx.value) / Decimal(10**18)) if tx.value else "0"

        # Use native token address for ETH
        native_token = "0x0000000000000000000000000000000000000000"

        try:
            out = await self._run_minara(
                "transfer",
                "-c", self._chain,
                "-t", native_token,
                "-a", amount_ether if amount_ether != "0" else "0.0001",
                "--to", tx.to,
                "-y",  # skip confirmation
                timeout=60,
            )
            elapsed = (time.perf_counter() - t0) * 1000

            # Try to extract tx hash from output
            tx_hash = ""
            hash_match = re.search(r"(0x[0-9a-fA-F]{64})", out)
            if hash_match:
                tx_hash = hash_match.group(1)

            return TxResult(
                tx_hash=tx_hash,
                elapsed_ms=elapsed,
                meta={"raw": out[:500]},
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            error_msg = str(exc).lower()
            if any(k in error_msg for k in (
                "insufficient", "balance", "revert", "rejected", "failed",
                "not enough", "zero", "no funds", "amount",
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
            "sign_message": False,
            "sign_typed_data": False,
            "send_transaction": True,
            "multi_chain": True,
            "policy_enforcement": False,
            "session_delegation": False,
            "estimate_gas": True,
        }

    def provider_unsupported(self) -> set[str]:
        # Minara API does not expose message signing or typed data signing
        return {"sign_message", "sign_typed_data"}

    async def estimate_gas(self, tx: TxParams) -> dict[str, Any]:
        """Use public RPC eth_estimateGas."""
        from adapters.base import eth_estimate_gas_rpc
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, eth_estimate_gas_rpc, tx.to, tx.value, tx.data,
            self._evm_address or None, "ethereum-sepolia",
        )
