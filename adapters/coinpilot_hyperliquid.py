from __future__ import annotations

import asyncio
import json
import re
import time
from pathlib import Path
from typing import Any

from adapters.base import SignResult, TxParams, TxResult, WalletAdapter, WalletInfo


class CoinpilotHyperliquidAdapter(WalletAdapter):
    name = "Coinpilot Hyperliquid"
    arch_class = "intent"
    chains = ["hyperliquid"]
    custody_model = "Privy-Managed"
    signing_modes = []
    submission_mode = "provider_submit"

    def __init__(self, config_path: str = "coinpilot.json", api_base_url: str = "", **kwargs: Any) -> None:
        self._config_path = Path(config_path).expanduser()
        self._api_base_url = api_base_url
        self._script_path = Path.cwd() / "scripts" / "coinpilot_cli.mjs"
        self._address: str = ""

    async def _run_cli(self, *args: str, timeout: float = 45) -> str:
        proc = await asyncio.create_subprocess_exec(
            "node",
            str(self._script_path),
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"coinpilot cli timed out: {' '.join(args)}")

        out = stdout.decode().strip()
        err = stderr.decode().strip()
        if proc.returncode != 0:
            raise RuntimeError(f"coinpilot cli exited {proc.returncode}: {(err or out)[:400]}")
        return out

    def _extract_address(self, text: str) -> str:
        m = re.search(r"\b(0x[0-9a-fA-F]{40})\b", text)
        return m.group(1) if m else ""

    def _load_address_from_config(self) -> str:
        if not self._config_path.exists():
            return ""
        try:
            data = json.loads(self._config_path.read_text(encoding="utf-8"))
        except Exception:
            return ""

        candidates: list[str] = []
        for key in (
            "wallet_address",
            "walletAddress",
            "primary_wallet",
            "primaryWallet",
            "address",
        ):
            v = data.get(key)
            if isinstance(v, str):
                candidates.append(v)

        wallets = data.get("wallets")
        if isinstance(wallets, list):
            for item in wallets:
                if isinstance(item, dict):
                    for key in ("address", "wallet_address", "walletAddress"):
                        v = item.get(key)
                        if isinstance(v, str):
                            candidates.append(v)

        for c in candidates:
            addr = self._extract_address(c)
            if addr:
                return addr
        return ""

    async def _discover_address_from_cli(self) -> str:
        for args in (("hl-account",), ("hl-portfolio",), ("validate",)):
            try:
                out = await self._run_cli(*args)
                addr = self._extract_address(out)
                if addr:
                    return addr
            except Exception:
                continue
        return ""

    async def setup(self) -> None:
        self._address = self._load_address_from_config()
        if not self._address and self._script_path.exists():
            self._address = await self._discover_address_from_cli()

    async def teardown(self) -> None:
        pass

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()
        if not self._address:
            self._address = self._load_address_from_config()
        if not self._address and self._script_path.exists():
            self._address = await self._discover_address_from_cli()
        elapsed = (time.perf_counter() - t0) * 1000
        return WalletInfo(
            address=self._address,
            chain="hyperliquid",
            meta={"elapsed_ms": elapsed, "config_path": str(self._config_path), "api_base_url": self._api_base_url},
        )

    async def sign_message(self, message: str) -> SignResult:
        raise NotImplementedError("Coinpilot Hyperliquid does not expose message signing")

    async def sign_typed_data(self, data: dict) -> SignResult:
        raise NotImplementedError("Coinpilot Hyperliquid does not expose typed data signing")

    async def send_transaction(self, tx: TxParams) -> TxResult:
        raise NotImplementedError("Coinpilot Hyperliquid executes via copy-trade subscriptions, not raw transactions")

    def capabilities(self) -> dict[str, bool]:
        return {
            "create_wallet": True,
            "sign_message": False,
            "sign_typed_data": False,
            "send_transaction": False,
            "multi_chain": False,
            "policy_enforcement": False,
            "session_delegation": False,
            "estimate_gas": False,
        }

    def provider_unsupported(self) -> set[str]:
        return {"sign_message", "sign_typed_data", "send_transaction"}
