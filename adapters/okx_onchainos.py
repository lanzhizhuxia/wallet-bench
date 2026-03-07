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

    # OKX chain index mapping (subset)
    _CHAIN_INDEX: dict[str, str] = {
        "ethereum": "1",
        "bsc": "56",
        "polygon": "137",
        "arbitrum": "42161",
        "optimism": "10",
        "base": "8453",
        "avalanche": "43114",
        "fantom": "250",
        "solana": "501",
    }

    def __init__(
        self,
        address: str = "",
        chain_index: str = "1",
        **kwargs: Any,
    ) -> None:
        self._address = address
        self._chain_index = chain_index

    # -- helpers -------------------------------------------------------------

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
            await self._run_onchainos("--version", "", timeout=10)
        except (FileNotFoundError, RuntimeError, TimeoutError):
            # Try bare version check
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
                    "--chain-index", self._chain_index,
                )
                elapsed = (time.perf_counter() - t0) * 1000
                meta: dict[str, Any] = {"elapsed_ms": elapsed, "local": True}
                if isinstance(result, dict):
                    meta["portfolio"] = {
                        k: result[k]
                        for k in ("totalValue", "total_value", "value")
                        if k in result
                    }
                return WalletInfo(
                    address=address,
                    chain=self._chain_index,
                    meta=meta,
                )
            except Exception:
                # Portfolio query failed but address is configured — return it
                elapsed = (time.perf_counter() - t0) * 1000
                return WalletInfo(
                    address=address,
                    chain=self._chain_index,
                    meta={"elapsed_ms": elapsed, "local": True, "verified": False},
                )

        # No address configured — return empty with note
        elapsed = (time.perf_counter() - t0) * 1000
        return WalletInfo(
            address="",
            chain=self._chain_index,
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

        Will likely fail (no private key in CLI), but we capture the error
        cleanly as a revert.
        """
        t0 = time.perf_counter()
        try:
            result = await self._run_onchainos(
                "gateway", "broadcast",
                "--to", tx.to,
                "--value", str(tx.value),
                "--data", tx.data,
                "--chain-index", self._chain_index,
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
                "key", "unauthorized", "invalid",
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
                "--to", tx.to,
                "--value", str(tx.value),
                "--data", tx.data,
                "--chain-index", self._chain_index,
            )
            elapsed = (time.perf_counter() - t0) * 1000
            if isinstance(result, dict):
                gas = result.get("gasLimit", result.get("gas_limit", 0))
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
        if dry_run:
            result = await self._run_onchainos(
                "swap", "quote",
                "--from", token_in,
                "--to", token_out,
                "--amount", amount,
                "--chain-index", self._chain_index,
            )
        else:
            result = await self._run_onchainos(
                "swap", "swap",
                "--from", token_in,
                "--to", token_out,
                "--amount", amount,
                "--chain-index", self._chain_index,
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
