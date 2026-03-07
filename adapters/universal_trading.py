from __future__ import annotations

import asyncio
import os
import re
import time
from pathlib import Path
from typing import Any

from adapters.base import SignResult, TxParams, TxResult, WalletAdapter, WalletInfo


class UniversalTradingAdapter(WalletAdapter):
    name = "Universal Trading (Particle Network)"
    arch_class = "local"
    chains = ["ethereum", "bsc", "polygon", "arbitrum", "optimism", "solana"]
    custody_model = "Local"
    signing_modes = ["raw_tx"]
    submission_mode = "client_submit"

    def __init__(self, repo_path: str = "", chain: str = "bsc", **kwargs: Any) -> None:
        self._chain = chain
        self._repo_path = Path(repo_path).expanduser() if repo_path else Path.cwd() / "universal-account-example"
        self._examples_path = self._repo_path / "examples"
        self._address: str = ""

    _ENV_ADDRESS_KEYS = (
        "UNIVERSAL_ACCOUNT_ADDRESS",
        "UA_EVM_ADDRESS",
        "SMART_ACCOUNT_ADDRESS",
        "WALLET_ADDRESS",
        "ADDRESS",
    )

    async def _run_cmd(self, *cmd: str, cwd: Path | None = None, timeout: float = 45,
                       allow_nonzero: bool = False) -> str:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            stdin=asyncio.subprocess.DEVNULL,
            cwd=str(cwd or self._repo_path),
            env={**os.environ},
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            raise TimeoutError(f"Command timed out: {' '.join(cmd)}")

        out = stdout.decode().strip()
        err = stderr.decode().strip()
        if proc.returncode != 0 and not allow_nonzero:
            raise RuntimeError(f"Command exited {proc.returncode}: {(err or out)[:400]}")
        return out or err

    def _extract_address(self, text: str) -> str:
        if self._chain == "solana":
            m = re.search(r"\b([1-9A-HJ-NP-Za-km-z]{32,44})\b", text)
            return m.group(1) if m else ""
        m = re.search(r"\b(0x[0-9a-fA-F]{40})\b", text)
        return m.group(1) if m else ""

    def _extract_ua_evm_address(self, text: str) -> str:
        m = re.search(r"Your\s+UA\s+EVM\s+Address\s*:\s*(0x[0-9a-fA-F]{40})", text, flags=re.IGNORECASE)
        if m:
            return m.group(1)
        return self._extract_address(text)

    def _extract_tx_hash(self, text: str) -> str:
        m = re.search(r"\b(0x[0-9a-fA-F]{64})\b", text)
        if m:
            return m.group(1)
        m = re.search(r"transactionId\s*[:=]\s*[\"']([^\"']+)[\"']", text, flags=re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"transactionId\s*[:=]\s*([^\s,}\]]+)", text, flags=re.IGNORECASE)
        return m.group(1) if m else ""

    def _read_env_address(self) -> str:
        env_candidates = [os.environ.get(key, "") for key in self._ENV_ADDRESS_KEYS]
        for value in env_candidates:
            addr = self._extract_address(value)
            if addr:
                return addr

        env_file = self._repo_path / ".env"
        if env_file.exists():
            text = env_file.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()
                if not stripped or stripped.startswith("#") or "=" not in stripped:
                    continue
                key, value = stripped.split("=", 1)
                if key.strip() not in self._ENV_ADDRESS_KEYS:
                    continue
                addr = self._extract_address(value.strip())
                if addr:
                    return addr
        return ""

    async def _read_sdk_address(self, timeout: float = 60) -> str:
        """Run warmup.ts to get UA address. Script may exit non-zero after printing address."""
        try:
            out = await self._run_cmd(
                "npx", "tsx", "examples/warmup.ts",
                cwd=self._repo_path, timeout=timeout, allow_nonzero=True,
            )
        except TimeoutError:
            return ""
        except Exception:
            return ""
        return self._extract_ua_evm_address(out)

    async def _ensure_address(self) -> str:
        if self._address:
            return self._address

        addr = self._read_env_address()
        if addr:
            self._address = addr
            return self._address

        if self._repo_path.exists() and self._examples_path.exists():
            addr = await self._read_sdk_address()
            if addr:
                self._address = addr

        return self._address

    async def setup(self) -> None:
        if self._examples_path.exists():
            await self._ensure_address()
        # If examples dir missing, tests will fail individually but runner won't crash

    async def teardown(self) -> None:
        pass

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()
        was_cached = bool(self._address)
        address = await self._ensure_address()

        if not address:
            init_script = self._repo_path / "init.sh"
            if init_script.exists():
                try:
                    out = await self._run_cmd("bash", str(init_script), cwd=self._repo_path, timeout=120)
                    self._address = self._extract_ua_evm_address(out)
                except Exception:
                    self._address = ""
                if not self._address:
                    self._address = await self._ensure_address()

        elapsed = (time.perf_counter() - t0) * 1000
        return WalletInfo(
            address=self._address,
            chain=self._chain,
            meta={
                "elapsed_ms": elapsed,
                "repo_path": str(self._repo_path),
                "source": "cache" if was_cached else ("sdk_or_env" if self._address else "unavailable"),
            },
        )

    async def sign_message(self, message: str) -> SignResult:
        raise NotImplementedError("Universal Trading does not expose message signing")

    async def sign_typed_data(self, data: dict) -> SignResult:
        raise NotImplementedError("Universal Trading does not expose typed data signing")

    async def send_transaction(self, tx: TxParams) -> TxResult:
        t0 = time.perf_counter()

        script_candidates = [
            "transfer-evm.ts",
            "send-evm.ts",
            "buy-evm.ts",
            "sell-evm.ts",
        ]
        if self._chain == "solana":
            script_candidates = ["transfer-solana.ts", "send-solana.ts", "buy-solana.ts", "sell-solana.ts"]

        script = ""
        for cand in script_candidates:
            p = self._examples_path / cand
            if p.exists():
                script = cand
                break

        if not script:
            elapsed = (time.perf_counter() - t0) * 1000
            return TxResult(
                tx_hash="",
                status=0,
                elapsed_ms=elapsed,
                meta={"revert": True, "error": "No suitable script found in examples/"},
            )

        try:
            out = await self._run_cmd("npx", "tsx", script, cwd=self._examples_path, timeout=120)
            tx_hash = self._extract_tx_hash(out)
            elapsed = (time.perf_counter() - t0) * 1000
            return TxResult(tx_hash=tx_hash, status=1 if tx_hash else None, elapsed_ms=elapsed, meta={"script": script, "raw": out[:500]})
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            return TxResult(
                tx_hash="",
                status=0,
                elapsed_ms=elapsed,
                meta={"script": script, "error": str(exc)[:300], "revert": True},
            )

    def capabilities(self) -> dict[str, bool]:
        return {
            "create_wallet": True,
            "sign_message": False,
            "sign_typed_data": False,
            "send_transaction": True,
            "multi_chain": True,
            "policy_enforcement": False,
            "session_delegation": False,
            "estimate_gas": self._chain != "solana",
        }

    def provider_unsupported(self) -> set[str]:
        return {"sign_message", "sign_typed_data"}
