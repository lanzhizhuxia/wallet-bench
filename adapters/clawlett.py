"""Clawlett adapter — executes local Node.js scripts via subprocess.

Clawlett is a Safe + Zodiac Roles based smart-account workflow on Base mainnet.
It exposes transaction-level operations (initialize/swap) but not personal_sign or
EIP-712 typed-data signing primitives.
"""

from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import Any

from adapters.base import SignResult, TxParams, TxResult, WalletAdapter, WalletInfo


class ClawlettAdapter(WalletAdapter):
    """Smart-account adapter for Clawlett Node.js scripts."""

    name = "Clawlett"
    arch_class = "smart_account"
    chains = ["base"]
    custody_model = "Safe+Zodiac-Roles"
    signing_modes = ["raw_tx"]
    submission_mode = "provider_submit"

    def __init__(
        self,
        safe_address: str = "",
        agent_key: str = "",
        owner_address: str = "",
        clawlett_repo_path: str = "",
        rpc_url: str = "https://mainnet.base.org",
        **kwargs: Any,
    ) -> None:
        self._safe_address = safe_address.strip()
        self._agent_key = agent_key.strip()
        self._owner_address = owner_address.strip()
        self._repo_path = Path(clawlett_repo_path).expanduser() if clawlett_repo_path else Path()
        self._rpc_url = rpc_url.strip() or "https://mainnet.base.org"

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def _extract_address(text: str) -> str:
        m = re.search(r"0x[0-9a-fA-F]{40}", text)
        return m.group(0) if m else ""

    @staticmethod
    def _extract_tx_hash(text: str) -> str:
        m = re.search(r"0x[0-9a-fA-F]{64}", text)
        return m.group(0) if m else ""

    def _script_path(self, script_name: str) -> Path:
        return self._repo_path / "scripts" / script_name

    async def _run_node_script(self, script_name: str, *args: str, timeout: float = 90) -> str:
        if not self._repo_path or not self._repo_path.is_dir():
            raise RuntimeError(
                "Clawlett repo not found. Set providers.clawlett.clawlett_repo_path to the cloned repo path."
            )

        script = self._script_path(script_name)
        if not script.exists():
            raise RuntimeError(f"Missing Clawlett script: {script}")

        cmd = ["node", str(script), *args]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(self._repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"Clawlett script timed out: {' '.join(cmd)}")

        out = stdout.decode().strip()
        err = stderr.decode().strip()
        combined = out if not err else f"{out}\n{err}".strip()

        if proc.returncode != 0:
            raise RuntimeError(f"Clawlett script failed ({proc.returncode}): {combined[:600]}")

        return combined

    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        if not self._repo_path or not self._repo_path.is_dir():
            # Repo not cloned — tests will fail individually but runner won't crash
            return
        if not self._owner_address or not self._agent_key:
            return

        required = ["initialize.js", "balance.js", "swap.js"]
        missing = [name for name in required if not self._script_path(name).exists()]
        if missing:
            return  # Scripts missing — tests will fail individually
    async def teardown(self) -> None:
        pass

    # -- core operations -----------------------------------------------------

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()

        # If a Safe already exists in config, return it directly.
        if self._safe_address and not self._safe_address.startswith("0xYOUR_"):
            elapsed = (time.perf_counter() - t0) * 1000
            return WalletInfo(
                address=self._safe_address,
                chain="base",
                meta={"elapsed_ms": elapsed, "source": "config.safe_address"},
            )

        out = await self._run_node_script("initialize.js", "--owner", self._owner_address)
        safe = self._extract_address(out)
        elapsed = (time.perf_counter() - t0) * 1000

        if not safe:
            raise RuntimeError("Clawlett initialize.js did not return a Safe address")

        self._safe_address = safe
        return WalletInfo(
            address=safe,
            chain="base",
            meta={"elapsed_ms": elapsed, "source": "initialize.js", "raw": out[:600]},
        )

    async def sign_message(self, message: str) -> SignResult:
        raise NotImplementedError(
            "Clawlett/Zodiac Roles does not expose personal_sign; only transaction-level operations are supported"
        )

    async def sign_typed_data(self, data: dict) -> SignResult:
        raise NotImplementedError(
            "Clawlett/Zodiac Roles does not expose signTypedData; only transaction-level operations are supported"
        )

    async def send_transaction(self, tx: TxParams) -> TxResult:
        t0 = time.perf_counter()

        args = [
            "--safe",
            self._safe_address,
            "--owner",
            self._owner_address,
            "--to",
            tx.to,
            "--value",
            str(tx.value),
            "--data",
            tx.data or "0x",
        ]

        try:
            out = await self._run_node_script("swap.js", *args, timeout=120)
            elapsed = (time.perf_counter() - t0) * 1000
            tx_hash = self._extract_tx_hash(out)
            return TxResult(tx_hash=tx_hash, elapsed_ms=elapsed, meta={"raw": out[:600]})
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            msg = str(exc).lower()
            if any(k in msg for k in ("blocked", "forbidden", "denied", "insufficient", "revert", "failed")):
                return TxResult(
                    tx_hash="",
                    status=0,
                    elapsed_ms=elapsed,
                    meta={"error": str(exc)[:600], "roles_restriction": True},
                )
            raise

    # -- introspection -------------------------------------------------------

    def capabilities(self) -> dict[str, bool]:
        return {
            "create_wallet": True,
            "sign_message": False,
            "sign_typed_data": False,
            "send_transaction": True,
            "multi_chain": False,
            "policy_enforcement": True,
            "session_delegation": False,
            "estimate_gas": True,
        }

    def provider_unsupported(self) -> set[str]:
        return {"sign_message", "sign_typed_data"}

    async def estimate_gas(self, tx: TxParams) -> dict[str, Any]:
        from adapters.base import eth_estimate_gas_rpc

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            eth_estimate_gas_rpc,
            tx.to,
            tx.value,
            tx.data,
            self._safe_address or None,
            "base",
            self._rpc_url,
        )
