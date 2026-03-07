from __future__ import annotations

import asyncio
import re
import time
from typing import Any

from adapters.base import SignResult, TxParams, TxResult, WalletAdapter, WalletInfo


class PolymarketAgentAdapter(WalletAdapter):
    name = "Polymarket Agent"
    arch_class = "local"
    chains = ["polygon"]
    custody_model = "Local"
    signing_modes = []
    submission_mode = "provider_submit"

    def __init__(self, chain: str = "polygon", **kwargs: Any) -> None:
        self._chain = chain
        self._address: str = ""

    async def _run_poly(self, *args: str, timeout: float = 45) -> str:
        proc = await asyncio.create_subprocess_exec(
            "poly",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"poly command timed out: poly {' '.join(args)}")

        out = stdout.decode().strip()
        err = stderr.decode().strip()
        if proc.returncode != 0:
            raise RuntimeError(f"poly exited {proc.returncode}: {(err or out)[:300]}")
        return out

    def _extract_address(self, text: str) -> str:
        match = re.search(r"\b(0x[0-9a-fA-F]{40})\b", text)
        return match.group(1) if match else ""

    async def _discover_address(self) -> str:
        for args in (("balance",), ("doctor",)):
            try:
                out = await self._run_poly(*args, timeout=30)
                addr = self._extract_address(out)
                if addr:
                    return addr
            except Exception:
                continue
        return ""

    async def setup(self) -> None:
        self._address = await self._discover_address()

    async def teardown(self) -> None:
        pass

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()
        if not self._address:
            try:
                await self._run_poly("setup", timeout=90)
            except Exception:
                pass
            self._address = await self._discover_address()

        elapsed = (time.perf_counter() - t0) * 1000
        return WalletInfo(address=self._address, chain=self._chain, meta={"elapsed_ms": elapsed})

    async def sign_message(self, message: str) -> SignResult:
        raise NotImplementedError("Polymarket Agent does not expose message signing")

    async def sign_typed_data(self, data: dict) -> SignResult:
        raise NotImplementedError("Polymarket Agent does not expose typed data signing")

    async def send_transaction(self, tx: TxParams) -> TxResult:
        raise NotImplementedError("Polymarket Agent has market buy/sell but no generic send_transaction")

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
