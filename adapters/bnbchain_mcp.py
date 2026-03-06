"""BNB Chain MCP adapter — talks to @bnb-chain/mcp via the mcp Python SDK."""

from __future__ import annotations

import json
import time
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from adapters.base import (
    SignResult,
    TxParams,
    TxResult,
    WalletAdapter,
    WalletInfo,
)

# BSC testnet chain ID — hardcoded safety constraint
_BSC_TESTNET_NETWORK = "bsc-testnet"
_BSC_TESTNET_CHAIN_ID = 97


class BnbChainMcpAdapter(WalletAdapter):
    """Local-class adapter for BNB Chain MCP server.

    Communicates with ``npx @bnb-chain/mcp@latest`` over stdio using the
    standard MCP client SDK.  The MCP server is transaction-oriented: it
    exposes ``transfer_native_token``, ``get_address_from_private_key``,
    ``estimate_gas``, ``get_native_balance``, etc.  It does **not** have
    ``personal_sign`` or ``signTypedData`` — we honestly report those as
    N/A-by-design.
    """

    name = "BNB Chain MCP"
    arch_class = "local"
    chains = ["bsc", "opbnb"]
    custody_model = "Local"
    signing_modes = ["raw_tx"]
    submission_mode = "client_submit"

    def __init__(self, private_key: str, network: str = _BSC_TESTNET_NETWORK) -> None:
        if network != _BSC_TESTNET_NETWORK:
            raise ValueError(
                f"Safety: only {_BSC_TESTNET_NETWORK} is allowed, got {network}"
            )
        self._private_key = private_key
        self._network = network
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None

    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        self._exit_stack = AsyncExitStack()
        server_params = StdioServerParameters(
            command="npx",
            args=["@bnb-chain/mcp@latest"],
            env={"PRIVATE_KEY": self._private_key},
        )
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()

    async def teardown(self) -> None:
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None

    # -- helpers -------------------------------------------------------------

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        assert self._session is not None, "call setup() first"
        result = await self._session.call_tool(name, arguments)
        # result.content is a list of TextContent / ImageContent etc.
        texts = [c.text for c in result.content if hasattr(c, "text")]
        combined = "\n".join(texts)
        # Try to parse as JSON; fall back to raw text
        try:
            return json.loads(combined)
        except (json.JSONDecodeError, TypeError):
            return combined

    # -- core operations -----------------------------------------------------

    async def create_wallet(self) -> WalletInfo:
        t0 = time.perf_counter()
        resp = await self._call_tool(
            "get_address_from_private_key",
            {"privateKey": self._private_key},
        )
        elapsed = (time.perf_counter() - t0) * 1000
        address = resp if isinstance(resp, str) else resp.get("address", str(resp))
        return WalletInfo(
            address=address,
            chain="bsc-testnet",
            meta={"elapsed_ms": elapsed, "raw": resp},
        )

    async def sign_message(self, message: str) -> SignResult:
        raise NotImplementedError("BNB Chain MCP does not support personal_sign")

    async def sign_typed_data(self, data: dict) -> SignResult:
        raise NotImplementedError("BNB Chain MCP does not support signTypedData")

    async def send_transaction(self, tx: TxParams) -> TxResult:
        t0 = time.perf_counter()
        # transfer_native_token params (from MCP schema):
        #   toAddress* (string), amount* (string, in BNB), network* (string)
        #   privateKey (optional, falls back to env)
        # Format as fixed-point decimal — viem rejects scientific notation
        from decimal import Decimal
        amount_bnb = str(Decimal(tx.value) / Decimal(10**18)) if tx.value else "0"
        resp = await self._call_tool(
            "transfer_native_token",
            {
                "toAddress": tx.to,
                "amount": amount_bnb,
                "network": self._network,
            },
        )
        elapsed = (time.perf_counter() - t0) * 1000
        tx_hash = ""
        if isinstance(resp, dict):
            tx_hash = resp.get("txHash", resp.get("transactionHash", resp.get("hash", "")))
        elif isinstance(resp, str) and resp.startswith("0x"):
            tx_hash = resp
        return TxResult(
            tx_hash=tx_hash,
            elapsed_ms=elapsed,
            meta={"raw": resp},
        )

    async def estimate_gas(self, tx: TxParams) -> dict[str, Any]:
        """Call the MCP estimate_gas tool (not part of ABC, used by t10)."""
        # estimate_gas schema: to* (string), value (ether string), network
        from decimal import Decimal
        value_ether = str(Decimal(tx.value) / Decimal(10**18)) if tx.value else "0"
        resp = await self._call_tool(
            "estimate_gas",
            {
                "to": tx.to,
                "value": value_ether,
                "network": self._network,
            },
        )
        return resp if isinstance(resp, dict) else {"raw": resp}

    async def get_balance(self, address: str) -> dict[str, Any]:
        """Call get_native_balance (helper for tests)."""
        resp = await self._call_tool(
            "get_native_balance",
            {"address": address, "network": self._network},
        )
        return resp if isinstance(resp, dict) else {"raw": resp}

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
        # MCP tool set has no personal_sign / signTypedData endpoints
        return {"sign_message", "sign_typed_data"}
