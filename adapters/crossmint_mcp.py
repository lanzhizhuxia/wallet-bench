"""Crossmint MCP adapter — checkout-focused, talks to mcp-crossmint-checkout via stdio.

This adapter communicates with the Crossmint MCP Server (mcp-crossmint-checkout)
which exposes 3 tools: create-order, check-order, get-usd-balance.

IMPORTANT: This MCP Server is checkout-only — wallet creation and signing happen
internally via the AGENT_WALLET_ADDRESS custodial wallet. For wallet_core tests
(t01-t04), use the REST adapter (adapters/crossmint.py) instead.

This adapter is useful for benchmarking Crossmint's unique App-layer capability:
purchasing real-world products (Amazon/Shopify) via an AI agent using on-chain
payment (credits/USDC on ethereum-sepolia).

Setup:
    git clone https://github.com/Crossmint/mcp-crossmint-checkout
    cd mcp-crossmint-checkout && npm install && npm run build
    # Then point server_path to build/index.js
"""

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

_DEFAULT_CHAIN = "ethereum-sepolia"


class CrossmintMcpAdapter(WalletAdapter):
    """Intent-class adapter for Crossmint MCP Server (checkout flow).

    Spawns ``node build/index.js`` from the mcp-crossmint-checkout repo and
    communicates via MCP stdio transport. The server handles wallet operations
    internally — it signs and submits transactions using AGENT_WALLET_ADDRESS.

    Tools available:
    - create-order: Purchase a product (Amazon/Shopify) via on-chain payment
    - check-order: Check order status
    - get-usd-balance: Get wallet USD balance (credits)
    """

    name = "Crossmint MCP (Checkout)"
    arch_class = "intent"
    chains = ["ethereum-sepolia"]
    custody_model = "Fireblocks-Custodial"
    signing_modes = ["raw_tx"]
    submission_mode = "provider_submit"

    def __init__(
        self,
        api_key: str = "",
        agent_wallet_address: str = "",
        server_path: str = "",
        recipient_email: str = "bench@example.com",
        recipient_name: str = "Wallet Bench",
        recipient_address: str = "123 Test St",
        recipient_city: str = "New York",
        recipient_state: str = "NY",
        recipient_postal_code: str = "10001",
        recipient_country: str = "US",
        **kwargs: Any,
    ) -> None:
        self._api_key = api_key
        self._agent_wallet_address = agent_wallet_address
        self._server_path = server_path  # path to mcp-crossmint-checkout/build/index.js
        self._recipient = {
            "RECIPIENT_EMAIL": recipient_email,
            "RECIPIENT_NAME": recipient_name,
            "RECIPIENT_ADDRESS_LINE1": recipient_address,
            "RECIPIENT_CITY": recipient_city,
            "RECIPIENT_STATE": recipient_state,
            "RECIPIENT_POSTAL_CODE": recipient_postal_code,
            "RECIPIENT_COUNTRY": recipient_country,
        }
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._tools: list[dict] = []

    # -- lifecycle -----------------------------------------------------------

    async def setup(self) -> None:
        if not self._server_path:
            raise RuntimeError(
                "CrossmintMcpAdapter requires 'server_path' pointing to "
                "mcp-crossmint-checkout/build/index.js. "
                "Clone and build: git clone https://github.com/Crossmint/mcp-crossmint-checkout "
                "&& cd mcp-crossmint-checkout && npm install && npm run build"
            )
        self._exit_stack = AsyncExitStack()
        env = {
            "CROSSMINT_API_KEY": self._api_key,
            "AGENT_WALLET_ADDRESS": self._agent_wallet_address,
            "ENVIRONMENT": "test",  # staging.crossmint.com + ethereum-sepolia
            **self._recipient,
        }
        server_params = StdioServerParameters(
            command="node",
            args=[self._server_path],
            env=env,
        )
        stdio_transport = await self._exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        read_stream, write_stream = stdio_transport
        self._session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )
        await self._session.initialize()

        # Cache available tools
        tools_result = await self._session.list_tools()
        self._tools = [
            {"name": t.name, "description": t.description}
            for t in tools_result.tools
        ]

    async def teardown(self) -> None:
        if self._exit_stack:
            await self._exit_stack.aclose()
            self._exit_stack = None
            self._session = None

    # -- helpers -------------------------------------------------------------

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        assert self._session is not None, "call setup() first"
        result = await self._session.call_tool(name, arguments)
        texts = [c.text for c in result.content if hasattr(c, "text")]
        combined = "\n".join(texts)
        try:
            return json.loads(combined)
        except (json.JSONDecodeError, TypeError):
            return combined

    # -- core operations (WalletAdapter ABC) ---------------------------------
    # Note: Crossmint MCP Server does not expose wallet/signing tools directly.
    # The wallet is managed internally via AGENT_WALLET_ADDRESS.
    # We implement the ABC methods to report this honestly.

    async def create_wallet(self) -> WalletInfo:
        """Return the pre-configured agent wallet address.

        The MCP server uses AGENT_WALLET_ADDRESS internally — there's no
        'create wallet' tool. We return the known address for test compatibility.
        """
        t0 = time.perf_counter()
        # Verify connectivity by checking balance
        resp = await self._call_tool("get-usd-balance", {})
        elapsed = (time.perf_counter() - t0) * 1000
        return WalletInfo(
            address=self._agent_wallet_address,
            chain=_DEFAULT_CHAIN,
            meta={
                "elapsed_ms": elapsed,
                "balance_check": resp,
                "note": "Wallet pre-provisioned via AGENT_WALLET_ADDRESS, not created via MCP tool",
            },
        )

    async def sign_message(self, message: str) -> SignResult:
        raise NotImplementedError(
            "Crossmint MCP Server does not expose signing tools. "
            "Signing happens internally during create-order. "
            "Use adapters/crossmint.py (REST) for sign_message tests."
        )

    async def sign_typed_data(self, data: dict) -> SignResult:
        raise NotImplementedError(
            "Crossmint MCP Server does not expose signing tools. "
            "Use adapters/crossmint.py (REST) for sign_typed_data tests."
        )

    async def send_transaction(self, tx: TxParams) -> TxResult:
        raise NotImplementedError(
            "Crossmint MCP Server does not expose raw transaction tools. "
            "Transactions happen internally during create-order. "
            "Use adapters/crossmint.py (REST) for send_transaction tests."
        )

    # -- checkout operations (Crossmint-specific) ----------------------------

    async def create_order(self, product_locator: str) -> dict[str, Any]:
        """Create a checkout order for a product.

        Args:
            product_locator: Product identifier, e.g.:
                - 'amazon:B00O79SKV6' (Amazon ASIN)
                - 'amazon:<full_amazon_url>'
                - 'shopify:<product-url>:<variant-id>'

        Returns:
            Dict with order_id, status, and raw response.
        """
        t0 = time.perf_counter()
        resp = await self._call_tool("create-order", {
            "lineItems": [{"productLocator": product_locator}],
        })
        elapsed = (time.perf_counter() - t0) * 1000
        return {
            "elapsed_ms": elapsed,
            "raw": resp,
            "success": not isinstance(resp, dict) or not resp.get("isError", False),
        }

    async def check_order(self, order_id: str) -> dict[str, Any]:
        """Check status of an existing order."""
        t0 = time.perf_counter()
        resp = await self._call_tool("check-order", {"orderId": order_id})
        elapsed = (time.perf_counter() - t0) * 1000
        return {"elapsed_ms": elapsed, "raw": resp}

    async def get_balance(self) -> dict[str, Any]:
        """Get USD balance (credits) of the agent wallet."""
        t0 = time.perf_counter()
        resp = await self._call_tool("get-usd-balance", {})
        elapsed = (time.perf_counter() - t0) * 1000
        return {"elapsed_ms": elapsed, "raw": resp}

    async def list_mcp_tools(self) -> list[dict]:
        """Return cached list of MCP tools (for test introspection)."""
        return self._tools

    # -- introspection -------------------------------------------------------

    def capabilities(self) -> dict[str, bool]:
        return {
            "create_wallet": True,   # returns pre-provisioned address
            "sign_message": False,   # not exposed via MCP
            "sign_typed_data": False,  # not exposed via MCP
            "send_transaction": False,  # not exposed via MCP (happens internally)
            "multi_chain": False,    # ethereum-sepolia only
            "policy_enforcement": False,
            "session_delegation": False,
            "estimate_gas": False,
            # Crossmint MCP-specific capabilities
            "checkout": True,        # unique: purchase real-world products
            "balance_check": True,   # USD credit balance
        }
