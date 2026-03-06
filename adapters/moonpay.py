"""MoonPay Agents adapter — talks to @moonpay/cli via subprocess."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any

from adapters.base import (
    SignResult,
    TxParams,
    TxResult,
    WalletAdapter,
    WalletInfo,
)


class MoonPayAdapter(WalletAdapter):
    """Local-class adapter for MoonPay Agents CLI.

    Uses ``mp`` CLI with ``--json`` flag for machine-readable output.
    MoonPay wallets are non-custodial BIP39 HD wallets with OS keychain
    encryption.  Keys never leave the local machine.
    """

    name = "MoonPay Agents"
    arch_class = "local"
    chains = [
        "ethereum", "base", "polygon", "arbitrum",
        "optimism", "bnb", "avalanche", "solana",
        "bitcoin", "tron",
    ]
    custody_model = "Local"
    signing_modes = ["personal_sign", "raw_tx"]
    submission_mode = "client_submit"

    def __init__(self, wallet_name: str = "bench", chain: str = "ethereum", **kwargs: Any) -> None:
        self._wallet_name = wallet_name
        self._chain = chain
        self._address: str = ""
        self._current_wallet: str = ""  # wallet name used for current session

    # -- helpers -------------------------------------------------------------

    async def _run_mp(self, *args: str, timeout: float = 30, _retries: int = 3) -> dict | list | str:
        """Run ``mp <args> --json`` and parse the JSON output.

        Automatically retries on rate-limit errors with exponential backoff.
        """
        cmd = ["mp", *args, "--json"]
        last_err: Exception | None = None

        for attempt in range(_retries):
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                raise TimeoutError(f"mp command timed out: {' '.join(cmd)}")

            out = stdout.decode().strip()
            err = stderr.decode().strip()

            if proc.returncode != 0:
                msg = (err or out)[:300]
                if "rate limit" in msg.lower() and attempt < _retries - 1:
                    wait = 2 ** attempt  # 1s, 2s, 4s
                    await asyncio.sleep(wait)
                    last_err = RuntimeError(f"mp exited {proc.returncode}: {msg}")
                    continue
                raise RuntimeError(f"mp exited {proc.returncode}: {msg}")

            try:
                return json.loads(out)
            except (json.JSONDecodeError, TypeError):
                return out

        raise last_err or RuntimeError(f"mp command failed after {_retries} retries")
    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        """Verify CLI is available and wallet exists."""
        wallets = await self._run_mp("wallet", "list")
        if isinstance(wallets, list):
            names = [w["name"] for w in wallets]
            if self._wallet_name not in names:
                raise RuntimeError(
                    f"Wallet '{self._wallet_name}' not found. "
                    f"Available: {names}. Run: mp wallet create --name {self._wallet_name}"
                )
            for w in wallets:
                if w["name"] == self._wallet_name:
                    self._address = w["addresses"].get(self._chain, "")
                    break
        self._current_wallet = self._wallet_name

    async def teardown(self) -> None:
        pass

    # -- core operations -----------------------------------------------------

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()

        # If we already have a wallet from setup(), return it (deterministic for tc01)
        if self._address and self._current_wallet:
            resp = await self._run_mp("wallet", "retrieve", "--wallet", self._current_wallet)
            elapsed = (time.perf_counter() - t0) * 1000
            if isinstance(resp, dict):
                address = resp.get("addresses", {}).get(self._chain, self._address)
            else:
                address = self._address
            return WalletInfo(
                address=address,
                chain=self._chain,
                meta={"elapsed_ms": elapsed, "wallet_name": self._current_wallet, "raw": resp},
            )

        # First call: create a new wallet
        wallet_name = f"bench-{uuid.uuid4().hex[:8]}"
        resp = await self._run_mp("wallet", "create", "--name", wallet_name)
        elapsed = (time.perf_counter() - t0) * 1000

        if isinstance(resp, dict):
            addresses = resp.get("addresses", {})
            address = addresses.get(self._chain, "")
            self._current_wallet = resp.get("name", wallet_name)
            self._address = address
        else:
            address = str(resp)

        return WalletInfo(
            address=address,
            chain=self._chain,
            meta={"elapsed_ms": elapsed, "wallet_name": self._current_wallet, "raw": resp},
        )

    async def sign_message(self, message: str) -> SignResult:
        t0 = time.perf_counter()
        resp = await self._run_mp(
            "message", "sign",
            "--wallet", self._current_wallet,
            "--chain", self._chain,
            "--message", message,
        )
        elapsed = (time.perf_counter() - t0) * 1000

        signature = ""
        if isinstance(resp, dict):
            signature = resp.get("signature", "")
        elif isinstance(resp, str):
            signature = resp

        return SignResult(
            signature=signature,
            signer=self._address,
            elapsed_ms=elapsed,
            meta={"raw": resp},
        )

    async def sign_typed_data(self, data: dict) -> SignResult:
        # MoonPay CLI supports message sign (EIP-191) but not EIP-712 typed data
        raise NotImplementedError("MoonPay CLI does not support EIP-712 signTypedData")

    async def send_transaction(self, tx: TxParams) -> TxResult:
        t0 = time.perf_counter()
        # MoonPay uses token transfer for native transfers.
        # Native token address for EVM: 0x0000000000000000000000000000000000000000
        native_token = "0x0000000000000000000000000000000000000000"
        from decimal import Decimal
        amount_ether = str(Decimal(tx.value) / Decimal(10**18)) if tx.value else "0"

        try:
            resp = await self._run_mp(
                "token", "transfer",
                "--wallet", self._current_wallet,
                "--chain", self._chain,
                "--token", native_token,
                "--amount", amount_ether,
                "--to", tx.to,
                timeout=60,
            )
            elapsed = (time.perf_counter() - t0) * 1000

            tx_hash = ""
            if isinstance(resp, dict):
                tx_hash = resp.get("transactionHash", resp.get("txHash", resp.get("hash", "")))
            elif isinstance(resp, str) and resp.startswith("0x"):
                tx_hash = resp

            return TxResult(
                tx_hash=tx_hash,
                elapsed_ms=elapsed,
                meta={"raw": resp},
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            error_msg = str(exc).lower()
            # Clean errors for expected failures (no balance, zero amount, etc.)
            if any(k in error_msg for k in (
                "insufficient", "balance", "revert", "rejected", "failed",
                "greater than zero", "amount must be",
            )):
                return TxResult(
                    tx_hash="",
                    elapsed_ms=elapsed,
                    status=0,
                    meta={"error": str(exc), "revert": True},
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
        # MoonPay CLI supports EIP-191 but not EIP-712 typed data
        return {"sign_typed_data"}

    async def estimate_gas(self, tx: TxParams) -> dict[str, Any]:
        """Use public RPC eth_estimateGas."""
        from adapters.base import eth_estimate_gas_rpc
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, eth_estimate_gas_rpc, tx.to, tx.value, tx.data,
            self._address or None, "ethereum-sepolia",
        )
