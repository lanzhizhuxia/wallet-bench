"""WalletAdapter abstract base class and shared data models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Test result model (used by cases → runner)
# ---------------------------------------------------------------------------

class TestStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"
    NOT_APPLICABLE = "not_applicable"
    UNSUPPORTED = "unsupported"        # Provider confirmed not to offer this capability
    INCONCLUSIVE = "inconclusive"      # Benchmark adapter not wired up; cannot determine

class TestResult(BaseModel):
    test_id: str
    test_name: str
    status: TestStatus
    elapsed_ms: float = 0.0
    message: str = ""
    detail: dict[str, Any] = Field(default_factory=dict)
    owner: str = ""  # 'provider' | 'benchmark' | 'industry' — who is responsible for this gap

# ---------------------------------------------------------------------------
# Adapter data models
# ---------------------------------------------------------------------------

class WalletInfo(BaseModel):
    address: str
    chain: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    meta: dict[str, Any] = Field(default_factory=dict)


class SignResult(BaseModel):
    signature: str = ""
    signer: str = ""
    message_hash: str = ""
    elapsed_ms: float = 0.0
    meta: dict[str, Any] = Field(default_factory=dict)


class TxParams(BaseModel):
    to: str
    value: int = 0  # wei
    data: str = "0x"
    chain_id: int | None = None
    gas_limit: int | None = None


class TxResult(BaseModel):
    tx_hash: str = ""
    block_number: int | None = None
    status: int | None = None  # 1 = success, 0 = revert
    gas_used: int | None = None
    elapsed_ms: float = 0.0
    meta: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class WalletAdapter(ABC):
    """Unified interface that every wallet provider adapter must implement."""

    name: str = ""
    arch_class: str = ""  # "local" | "api_custodial" | "intent" | "tee" | "mpc_aa"
    chains: list[str] = []
    custody_model: str = ""
    signing_modes: list[str] = []
    submission_mode: str = ""

    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        """Initialise connections / spawn sub-processes."""

    async def teardown(self) -> None:
        """Clean up resources."""

    # -- core operations -----------------------------------------------------

    @abstractmethod
    async def create_wallet(self) -> WalletInfo:
        """Create (or derive) a wallet and return its info."""

    @abstractmethod
    async def sign_message(self, message: str) -> SignResult:
        """Sign an arbitrary message (EIP-191 / personal_sign)."""

    @abstractmethod
    async def sign_typed_data(self, data: dict) -> SignResult:
        """Sign EIP-712 typed data."""

    @abstractmethod
    async def send_transaction(self, tx: TxParams) -> TxResult:
        """Build, sign, and submit a transaction."""

    # -- introspection -------------------------------------------------------

    def capabilities(self) -> dict[str, bool]:
        """Return a map of capability → supported.

        The runner inspects this to decide whether to run or SKIP a test.
        """
        return {
            "create_wallet": True,
            "sign_message": True,
            "sign_typed_data": True,
            "send_transaction": True,
            "multi_chain": False,
            "policy_enforcement": False,
            "session_delegation": False,
            "estimate_gas": False,
        }

    def provider_unsupported(self) -> set[str]:
        """Capabilities the *provider* confirmed not to offer.

        Items here are reported as UNSUPPORTED (owner=provider) rather than
        INCONCLUSIVE (owner=benchmark) when the corresponding capability is
        False in capabilities().
        """
        return set()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

# Public Sepolia RPC endpoints (fallback chain)
_PUBLIC_RPC: dict[str, str] = {
    "ethereum-sepolia": "https://ethereum-sepolia-rpc.publicnode.com",
    "base-sepolia": "https://sepolia.base.org",
    "polygon-amoy": "https://rpc-amoy.polygon.technology",
    "arbitrum-sepolia": "https://sepolia-rollup.arbitrum.io/rpc",
    "optimism-sepolia": "https://sepolia.optimism.io",
    # chain-id based fallbacks
    "11155111": "https://ethereum-sepolia-rpc.publicnode.com",
    "84532": "https://sepolia.base.org",
    "97": "https://data-seed-prebsc-1-s1.bnbchain.org:8545",
}


def eth_estimate_gas_rpc(
    to: str,
    value_wei: int = 0,
    data: str = "0x",
    from_addr: str | None = None,
    chain: str = "ethereum-sepolia",
    rpc_url: str | None = None,
) -> dict[str, Any]:
    """Call eth_estimateGas via JSON-RPC. Returns {gas_estimate: int, rpc_url: str}."""
    import json as _json
    from urllib.request import Request, urlopen

    url = rpc_url or _PUBLIC_RPC.get(chain, "https://ethereum-sepolia-rpc.publicnode.com")
    tx_obj: dict[str, Any] = {"to": to, "data": data}
    if value_wei:
        tx_obj["value"] = hex(value_wei)
    if from_addr:
        tx_obj["from"] = from_addr
    payload = {
        "jsonrpc": "2.0",
        "method": "eth_estimateGas",
        "params": [tx_obj],
        "id": 1,
    }
    req = Request(url, data=_json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "wallet-bench/1.0")
    with urlopen(req, timeout=15) as resp:
        result = _json.loads(resp.read())
    if "error" in result:
        raise RuntimeError(f"eth_estimateGas error: {result['error']}")
    gas_hex = result.get("result", "0x0")
    return {"gas_estimate": int(gas_hex, 16), "rpc_url": url}
