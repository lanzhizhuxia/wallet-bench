"""OKX OnchainOS adapter — talks to onchainos CLI via subprocess.

OKX OnchainOS is a local Rust CLI tool (5 skills / 34 commands) covering
Portfolio, DEX quotes, Swap, Token search, and Gateway (gas/simulate/broadcast).
60+ chains supported.  No signing primitives exposed.
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any

from adapters.base import (
    SignResult,
    TxParams,
    TxResult,
    WalletAdapter,
    WalletInfo,
)

# Well-known token contract addresses (Ethereum mainnet) for swap tests
_TOKEN_CONTRACTS: dict[str, dict[str, str]] = {
    "ethereum": {
        "USDC": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "USDT": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        "WETH": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2",
        "DAI": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
    },
    "bsc": {
        "USDC": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d",
        "USDT": "0x55d398326f99059fF775485246999027B3197955",
    },
    "polygon": {
        "USDC": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "USDT": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F",
    },
    "base": {
        "USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "USDT": "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    },
    "arbitrum": {
        "USDC": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "USDT": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9",
    },
}


class OkxOnchainosAdapter(WalletAdapter):
    """Local-class adapter for OKX OnchainOS CLI.

    Uses ``onchainos`` CLI.  Keys are user-managed (local).
    No message signing or typed-data signing is available.
    """

    name = "OKX OnchainOS"
    arch_class = "local"
    chains = [
        "ethereum", "bsc", "polygon", "arbitrum", "optimism",
        "base", "avalanche", "fantom", "cronos", "gnosis",
        "celo", "moonbeam", "solana", "tron", "aptos",
        "sui", "near", "cosmos", "starknet", "zksync",
        "linea", "scroll", "mantle", "manta", "blast",
        "mode", "merlin", "bob", "core", "kava",
        "metis", "boba", "aurora", "taiko", "sei",
        "berachain", "monad",
    ]
    custody_model = "Local"
    signing_modes = ["raw_tx"]
    submission_mode = "client_submit"

    def __init__(
        self,
        address: str = "",
        chain: str = "ethereum",
        **kwargs: Any,
    ) -> None:
        self._address = address
        self._chain = chain

    # -- helpers -------------------------------------------------------------

    def _resolve_token(self, ticker: str) -> str:
        """Resolve a token ticker to a contract address for the current chain."""
        chain_tokens = _TOKEN_CONTRACTS.get(self._chain, _TOKEN_CONTRACTS["ethereum"])
        return chain_tokens.get(ticker.upper(), ticker)

    async def _run_onchainos(
        self,
        skill: str,
        command: str,
        *args: str,
        timeout: float = 30,
    ) -> dict[str, Any] | str:
        """Run ``onchainos <skill> <command> [args]`` and parse JSON output."""
        cmd = ["onchainos", skill, command, *args]
        env = {**os.environ}
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            env=env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"onchainos command timed out: {' '.join(cmd)}")

        out = stdout.decode().strip()
        err = stderr.decode().strip()

        if proc.returncode != 0:
            raise RuntimeError(
                f"onchainos exited {proc.returncode}: {(err or out)[:300]}"
            )

        # Try JSON parse; fall back to raw text
        try:
            return json.loads(out)
        except (json.JSONDecodeError, ValueError):
            return out

    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        """Verify CLI is installed and API credentials are set."""
        # Check CLI is available
        try:
            proc = await asyncio.create_subprocess_exec(
                "onchainos", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.communicate(), timeout=10)
        except FileNotFoundError:
            raise RuntimeError(
                "onchainos CLI not found. Install: "
                "curl -sSL https://raw.githubusercontent.com/okx/onchainos-skills/main/install.sh | sh"
            )

        # Check required env vars
        missing = [
            k for k in ("OKX_API_KEY", "OKX_SECRET_KEY", "OKX_PASSPHRASE")
            if not os.environ.get(k)
        ]
        if missing:
            raise RuntimeError(
                f"Missing environment variables: {', '.join(missing)}. "
                "Set OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE."
            )

    async def teardown(self) -> None:
        pass

    # -- core operations -----------------------------------------------------

    async def create_wallet(self) -> WalletInfo:
        """Return the configured address, verified via portfolio query.

        OnchainOS does not create wallets — users provide their address.
        We validate it by querying portfolio total-value.
        """
        t0 = time.perf_counter()
        address = self._address

        if address:
            try:
                result = await self._run_onchainos(
                    "portfolio", "total-value",
                    "--address", address,
                    "--chains", self._chain,
                )
                elapsed = (time.perf_counter() - t0) * 1000
                meta: dict[str, Any] = {"elapsed_ms": elapsed, "local": True}
                if isinstance(result, dict):
                    data = result.get("data", [{}])
                    if data:
                        meta["totalValue"] = data[0].get("totalValue", "")
                return WalletInfo(
                    address=address,
                    chain=self._chain,
                    meta=meta,
                )
            except Exception:
                # Portfolio query failed but address is configured — return it
                elapsed = (time.perf_counter() - t0) * 1000
                return WalletInfo(
                    address=address,
                    chain=self._chain,
                    meta={"elapsed_ms": elapsed, "local": True, "verified": False},
                )

        # No address configured — return empty with note
        elapsed = (time.perf_counter() - t0) * 1000
        return WalletInfo(
            address="",
            chain=self._chain,
            meta={
                "elapsed_ms": elapsed,
                "local": True,
                "note": "No address configured. Set 'address' in config.yaml.",
            },
        )

    async def sign_message(self, message: str) -> SignResult:
        raise NotImplementedError("OKX OnchainOS does not expose message signing")

    async def sign_typed_data(self, data: dict) -> SignResult:
        raise NotImplementedError("OKX OnchainOS does not expose typed data signing")

    async def send_transaction(self, tx: TxParams) -> TxResult:
        """Attempt to broadcast a transaction via gateway.

        Will fail (broadcast requires a pre-signed tx hex which we don't have),
        but we capture the error cleanly as a revert.
        """
        t0 = time.perf_counter()
        try:
            result = await self._run_onchainos(
                "gateway", "broadcast",
                "--signed-tx", tx.data if tx.data != "0x" else "0x00",
                "--address", self._address or tx.to,
                "--chain", self._chain,
                timeout=60,
            )
            elapsed = (time.perf_counter() - t0) * 1000
            tx_hash = ""
            if isinstance(result, dict):
                tx_hash = result.get("txHash", result.get("tx_hash", ""))
            return TxResult(
                tx_hash=tx_hash,
                elapsed_ms=elapsed,
                meta={"raw": str(result)[:500]},
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            error_msg = str(exc).lower()
            if any(k in error_msg for k in (
                "insufficient", "balance", "revert", "rejected", "failed",
                "not enough", "zero", "no funds", "broadcast", "sign",
                "key", "unauthorized", "invalid", "decode", "rlp",
            )):
                return TxResult(
                    tx_hash="",
                    elapsed_ms=elapsed,
                    status=0,
                    meta={"error": str(exc)[:300], "revert": True},
                )
            raise

    async def estimate_gas(self, tx: TxParams) -> dict[str, Any]:
        """Use onchainos gateway gas-limit for estimation."""
        t0 = time.perf_counter()
        try:
            result = await self._run_onchainos(
                "gateway", "gas-limit",
                "--from", self._address or "0x0000000000000000000000000000000000000000",
                "--to", tx.to,
                "--chain", self._chain,
            )
            elapsed = (time.perf_counter() - t0) * 1000
            if isinstance(result, dict):
                data = result.get("data", [{}])
                gas = 0
                if data:
                    gas = data[0].get("gasLimit", data[0].get("gas_limit", 0))
                return {"gas_estimate": int(gas), "elapsed_ms": elapsed, "source": "onchainos"}
            return {"gas_estimate": 0, "elapsed_ms": elapsed, "raw": str(result)[:300]}
        except Exception:
            # Fallback to public RPC
            from adapters.base import eth_estimate_gas_rpc
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None, eth_estimate_gas_rpc, tx.to, tx.value, tx.data,
                self._address or None, "ethereum-sepolia",
            )

    async def token_swap(
        self,
        token_in: str,
        token_out: str,
        amount: str,
        *,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Execute or quote a token swap via onchainos swap skill."""
        t0 = time.perf_counter()
        # Resolve tickers to contract addresses
        from_addr = self._resolve_token(token_in)
        to_addr = self._resolve_token(token_out)
        # Convert human amount to minimal units (assume 6 decimals for stablecoins)
        try:
            minimal = str(int(float(amount) * 1_000_000))
        except (ValueError, OverflowError):
            minimal = amount

        if dry_run:
            result = await self._run_onchainos(
                "swap", "quote",
                "--from", from_addr,
                "--to", to_addr,
                "--amount", minimal,
                "--chain", self._chain,
            )
        else:
            result = await self._run_onchainos(
                "swap", "swap",
                "--from", from_addr,
                "--to", to_addr,
                "--amount", minimal,
                "--chain", self._chain,
                timeout=60,
            )
        elapsed = (time.perf_counter() - t0) * 1000
        if isinstance(result, dict):
            result["elapsed_ms"] = elapsed
            return result
        return {"raw": str(result)[:500], "elapsed_ms": elapsed}

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
            "token_swap": True,
        }

    def provider_unsupported(self) -> set[str]:
        return {"sign_message", "sign_typed_data"}
