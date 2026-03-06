# DeFi Integration Cost Matrix v1

**Date**: 2026-03-06
**Version**: v1
**Status**: Normative
**Evaluator**: claude-opus-4.6 (AI agent) + librarian research agents

---

## 1. Scope & Assumptions

### 评测范围
- **6 家钱包提供商**: Privy, Coinbase AgentKit, Crossmint, BNB Chain MCP, MoonPay, Minara
- **4 个 DeFi 场景**: Uniswap V3 Swap, Aave V3/Morpho Blue 借贷, Hyperliquid 永续合约, Polymarket 预测市场
- **评估视角**: AI Agent 对接各协议的额外开发成本（二次开发成本）

### 评级定义

| 评级 | 标签 | 工时 | 含义 |
|------|------|------|------|
| 🟢 Simple | `simple` | < 1 天 | 提供商内置功能或 Agent 仅需转发 calldata |
| 🟡 Medium | `medium` | 1-3 天 | Agent 需编码 calldata 或构建签名适配器，但钱包可处理签名/提交 |
| 🟠 Complex | `complex` | 3-5 天 | 需要大量定制代码或不确定的 workaround |
| 🔴 Not Feasible | `not_feasible` | — | 架构层面无法实现，无 workaround |

### 前置假设
- Agent 运行环境为服务端 (server-side)，非浏览器嵌入
- 评测关注"能否对接 + 对接成本"，不含协议本身的学习成本
- 链范围：Ethereum mainnet/Sepolia, Base, Polygon (Polymarket), Hyperliquid L1 (Hyperliquid)
- 所有评估基于 2026-03-05 的公开文档和 SDK 源码

---

## 2. 架构决定性因素

DeFi 对接可行性由两个关键能力决定：

| 能力 | 解锁的场景 | 具备的提供商 |
|------|-----------|-------------|
| **`send_transaction` + arbitrary calldata** | 链上 DeFi (Uniswap swap, Aave/Morpho 借贷) | Privy ✅, Coinbase ✅, Crossmint ✅, BNB MCP ✅ |
| **`eth_signTypedData_v4` (EIP-712)** | 链下协议签名 (Hyperliquid 永续, Polymarket CLOB) | Privy ✅, Coinbase ✅, Crossmint ✅ |

**缺少任一能力的提供商在对应场景中评为 Not Feasible。**

---

## 3. 综合矩阵

| 提供商 | 🔄 Uniswap Swap | 🏦 Aave/Morpho 借贷 | 📈 Hyperliquid 永续 | 🎰 Polymarket 预测 | 覆盖率 |
|--------|:---:|:---:|:---:|:---:|:---:|
| **Privy** | 🟡 低门槛 (1-2d) | 🟡 低门槛 (1-2d) | 🟡 低门槛 (1-2d) | 🟠 中等 (2-3d) | **4/4** |
| **Coinbase AgentKit** | 🟢 即用 (<1d) | 🟢 即用 (<1d) | 🟡 低门槛 (1-2d) | 🟠 中等 (2-4d) | **4/4** |
| **Crossmint** | 🟡 低门槛 (1-2d) | 🟡 低门槛 (1-2d) | 🟡 低门槛 (1-2d) | 🟠 中等 (2-3d) | **4/4** |
| **BNB Chain MCP** | 🟡 低门槛 (2-3d) | 🟠 中等 (2-3d) | 🔴 不可行 | 🔴 不可行 | **2/4** |
| **MoonPay** | 🔴 不可行 | 🔴 不可行 | 🔴 不可行 | 🔴 不可行 | **0/4** |
| **Minara** | 🟢 即用†(聚合器) | 🔴 不可行 | 🔴 不可行 | 🔴 不可行 | **0~1/4** |

---

## 4. 逐场景详细分析

### 4.1 Uniswap V3 Swap

**协议要求**: Agent 需向 Uniswap SwapRouter 发送 ABI 编码的 `exactInputSingle()` calldata，前置 ERC-20 `approve()` 交易。

> **生态加速器**: Uniswap Trading API (REST: `check_approval → quote → swap`) 可提供预编码 calldata，降低 Medium 评级的实际工作量至 ~0.5-1 天。Uniswap 于 2026 年 2 月发布 `uniswap-ai` AI 开发工具包 ([github.com/Uniswap/uniswap-ai](https://github.com/Uniswap/uniswap-ai))，提供 swap-integration skill，进一步降低编码门槛。

| 提供商 | 评级 | 路径 | 依据 |
|--------|------|------|------|
| **Privy** | 🟡 Medium (1-2d) | `eth_sendTransaction` + `data` field via REST `/wallets/{id}/rpc` | Agent 编码 calldata（或调 Uniswap Trading API），Privy 签名提交。支持任意 caip2 链。 |
| **Coinbase AgentKit** | 🟢 Simple (<1d) | 内置 `swap` action (CDP Swap API / 0x 聚合器) | `swap(from_token, to_token, from_amount)` 一行代码。自动处理 Permit2 approval + slippage。**⚠️ 仅限 Base/ETH mainnet，Sepolia 不支持。** |
| **Crossmint** | 🟡 Medium (1-2d) | `sendTransaction({to, value, data})` via REST API | 与 Privy 同级。Agent 编码 calldata，Crossmint 签名。支持多链 EVM。 |
| **BNB Chain MCP** | 🟡 Medium (2-3d) | `write_contract` MCP tool + `approve_token_spending` | Agent 需提供完整 Uniswap Router ABI + args。无原生 swap tool（Coming soon）。BSC 为主，ETH/Base 需额外配置。 |
| **MoonPay** | 🔴 Not Feasible | 无 raw calldata 接口 | MoonPay CLI 是 KYC 门控的聚合器 swap，无 `send-tx --data` 命令。无法向 Uniswap Router 发送 calldata。 |
| **Minara** | 🟢 Simple† | `minara swap` 聚合器命令 | **†托管聚合器，非 Uniswap V3 Router 直调。** 如需精确控制 fee tier / 路由则 Not Feasible。如接受"任意 DEX swap"则 Simple。 |

### 4.2 Aave V3 / Morpho Blue 借贷

**协议要求**: 多步骤交易 — ERC-20 `approve()` + `Pool.supply()` / `Pool.borrow()` 等。需要 ABI 编码 + 交易排序。Health factor 监控为只读 RPC 调用。

| 提供商 | 评级 | 路径 | 依据 |
|--------|------|------|------|
| **Privy** | 🟡 Medium (1-2d) | `eth_sendTransaction` 发两笔 tx (approve + supply) | Agent 负责 ABI 编码和 tx 排序。Privy 文档提示 Morpho/Aave yield vault RPC intent 可能在开发中。 |
| **Coinbase AgentKit** | 🟢 Simple (<1d) | 内置 `AaveActionProvider` + `MorphoActionProvider` | 6 个现成 action: `supply/withdraw/borrow/repay/get_portfolio/set_collateral`。自动处理 approval。**⚠️ Aave 仅限 Base；Morpho = MetaMorpho vault（非 Morpho Blue 核心借贷）。** |
| **Crossmint** | 🟡 Medium (1-2d) | `sendTransaction({to, data})` 多步骤 | 与 Privy 同级。Agent 编码 + 排序，Crossmint 签名。 |
| **BNB Chain MCP** | 🟡 Medium (2-3d) | `write_contract` + `approve_token_spending` | 可行但需配置非 BSC 链。Aave V3 在 BSC 有部署但资产有限；Morpho Blue 无 BSC 部署。 |
| **MoonPay** | 🔴 Not Feasible | 无 raw calldata 接口 | 同 Uniswap — 无法发送自定义合约调用。 |
| **Minara** | 🔴 Not Feasible | 无借贷命令、无 raw calldata | 托管 CLI 仅有 swap/transfer/perps，无 deposit/lend/supply 等 DeFi 原语。 |

### 4.3 Hyperliquid 永续合约

**协议要求**: 两套签名方案 —
- **Scheme A** (`sign_l1_action`): 所有交易操作。msgpack 编码 → keccak256 → EIP-712 `Agent` type (chainId: 1337)
- **Scheme B** (`sign_user_signed_action`): 转账/提现/Agent 授权。EIP-712 `HyperliquidSignTransaction` domain (chainId: 421614)
- SDK (`hyperliquid-python-sdk`) 硬编码 `LocalAccount`，无外部 signer 接口
- **API Wallet 模式**: 用主钱包签一次 `approveAgent`（Scheme B），后续用本地临时密钥交易（Scheme A）

| 提供商 | 评级 | 路径 | 依据 |
|--------|------|------|------|
| **Privy** | 🟡 低门槛 (1-2d) | API Wallet 模式: Privy REST signTypedData 签 `approveAgent` → 本地临时 key 交易 | Privy 支持 `eth_signTypedData_v4`，但 Hyperliquid 使用自定义 EIP-712 domain（chainId 1337/421614），需 Agent 自行构造 typed data。非即用，需约 1-2d 编码。 |
| **Coinbase AgentKit** | 🟡 低门槛 (1-2d) | 同上: CDP `sign_typed_data` 签 approveAgent → 本地临时 key | CDP sign_typed_data 支持 EIP-712，但无内置 Hyperliquid action，需 Agent 自行构造 typed data + 调用 SDK。 |
| **Crossmint** | 🟡 Medium (1-2d) | REST `signatures` endpoint 签 `approveAgent` → 本地临时 key | 需验证 Crossmint 的 typed data signing endpoint 能否处理 HL 的自定义 EIP-712 domain。 |
| **BNB Chain MCP** | 🔴 Not Feasible | 无 `signTypedData` / `personal_sign` 工具 | MCP 仅暴露链上交易工具，无消息签名。无法完成 Scheme A 或 Scheme B。 |
| **MoonPay** | 🔴 Not Feasible | 仅 `personal_sign`，无 `signTypedData` | `personal_sign` 添加 `\x19Ethereum Signed Message` 前缀，与 EIP-712 不兼容。Hyperliquid 会拒绝签名。 |
| **Minara** | 🔴 Not Feasible | 无签名接口 | 托管系统不暴露任何消息签名 API。 |

### 4.4 Polymarket 预测市场

**协议要求**:
- **Path A (CLI)**: `polymarket-cli` (Rust) 需要 raw private key
- **Path B (CLOB API)**: EIP-712 签名 → 提交到 Polymarket CLOB REST API
- `py-clob-client` 硬编码 `signer.private_key` 属性访问（builder.py L153），无法注入外部 signer
- Polygon 链 (chain_id: 137)，USDC 为交易媒介

| 提供商 | 评级 | 路径 | 依据 |
|--------|------|------|------|
| **Privy** | 🟡 Medium (2-3d) | Path B: `eth_signTypedData_v4` via REST → 自建 EIP-712 encoder → CLOB API | 需实现 `ClobAuth` (L1) + `Order` struct (L2) 的 EIP-712 编码。Polygon 链支持确认。 |
| **Coinbase AgentKit** | 🟠 Medium-Complex (2-4d) | Path B: CDP `sign/typed-data` API | EIP-712 签名能力确认。**⚠️ Polygon (137) 支持待验证** — 如 Base-only 需跨链桥接，复杂度升至 Complex。 |
| **Crossmint** | 🟡 Medium (2-3d) | Path B: REST `signatures` endpoint + 自建 EIP-712 encoder | 与 Privy 同级路径。需验证 signatures endpoint 对 Polymarket domain 的兼容性。 |
| **BNB Chain MCP** | 🔴 不可行 | 无路径 | Polymarket CLOB 需要 EIP-712 签名（ClobAuth + Order），BNB Chain MCP 不支持 signTypedData。且 Polymarket 运行在 Polygon（chain 137），非 BSC 链。 |
| **MoonPay** | 🔴 不可行 | 无路径 | Polymarket CLOB 需要 EIP-712 签名，MoonPay 仅支持 personal_sign，与 EIP-712 不兼容。密钥提取注入 CLI 也不可行——MoonPay CLI 不暴露原始私钥导出接口。 |
| **Minara** | 🔴 Not Feasible | 无路径 | 托管系统不暴露密钥也不暴露签名接口。 |

---

## 5. 关键发现

### 5.1 三个梯队

| 梯队 | 提供商 | DeFi 覆盖 | 核心特征 |
|------|--------|----------|----------|
| **T1: 全通型** | Privy, Coinbase AgentKit, Crossmint | 4/4 | calldata + EIP-712 双能力完备 |
| **T2: 部分通型** | BNB Chain MCP | 2/4 | 有 calldata 无 EIP-712 → 链下协议（Hyperliquid/Polymarket）均不可行 |
| **T3: 受限型** | MoonPay, Minara | 0~1/4 | 缺少 programmable wallet 基础能力 |

### 5.2 Coinbase 的 "内置优势"

Coinbase AgentKit 内置了 Uniswap (CDP Swap)、Aave V3 (`AaveActionProvider`)、Morpho (`MorphoActionProvider`) 的现成 action — **DeFi 开箱即用成本最低**。但有两个限制：
- **链覆盖**: Aave 仅 Base，swap 仅 Base/ETH mainnet
- **Polymarket**: Polygon 链支持存疑，可能需跨链

### 5.3 API Wallet / Proxy Signer 模式

Hyperliquid 和 Polymarket 都支持"代理钱包"模式 — 主钱包签一次授权，后续用本地临时密钥操作。这使得 TEE 钱包（Privy/Coinbase）只需一次远程签名调用，显著降低延迟和复杂度。

### 5.4 协议 SDK 的外部 signer 支持缺失

- `hyperliquid-python-sdk`: 硬编码 `LocalAccount`（`exchange.py` L63-66）
- `py-clob-client`: 硬编码 `signer.private_key` 属性访问（`builder.py` L153）

**这是行业性问题** — 多数 DeFi SDK 假设本地密钥，不支持外部 signer 注入。API 钱包提供商需要绕过 SDK 直接调用底层 REST API。

---

## 6. 集成加速器

| 工具 | 类型 | 影响 |
|------|------|------|
| [Uniswap Trading API](https://api-docs.uniswap.org) | REST API | 为 Medium 评级的 swap 场景提供预编码 calldata，降低编码工作量 |
| [uniswap-ai](https://github.com/Uniswap/uniswap-ai) | AI Coding Skill | 开发者编码辅助，不改变 runtime 能力 |
| [polymarket-cli](https://github.com/Polymarket/polymarket-cli) | Rust CLI | 本地密钥提供商可直接使用 CLI 绕过 SDK |
| Hyperliquid API Wallet | 协议特性 | 一次性 EIP-712 bootstrap 后可用本地密钥交易 |

**注意**: 这些工具降低实际工作量，但不改变提供商的能力评级（Simple/Medium/Not Feasible 的分级基于架构能力，非工具可用性）。

---

## 7. 证据链接

### Hyperliquid SDK 源码
- `Exchange.__init__` hardcodes `LocalAccount`: [`exchange.py#L63-L66`](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/b4d2d1bfde9bfb3411fec3f781e3981b48a1a0c5/hyperliquid/exchange.py#L63-L66)
- `sign_l1_action` (Scheme A): [`signing.py#L173-L243`](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/b4d2d1bfde9bfb3411fec3f781e3981b48a1a0c5/hyperliquid/utils/signing.py#L173-L243)
- `sign_user_signed_action` (Scheme B): [`signing.py#L246-L252`](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/b4d2d1bfde9bfb3411fec3f781e3981b48a1a0c5/hyperliquid/utils/signing.py#L246-L252)
- `approveAgent`: [`exchange.py#L615-L637`](https://github.com/hyperliquid-dex/hyperliquid-python-sdk/blob/b4d2d1bfde9bfb3411fec3f781e3981b48a1a0c5/hyperliquid/exchange.py#L615-L637)

### Polymarket SDK/CLI 源码
- `py-clob-client` Signer 硬编码: [`signer.py`](https://github.com/Polymarket/py-clob-client/blob/cc1740c11adf0be33590c1ee4976ce8bfd2f37c2/py_clob_client/signer.py)
- Builder 直接访问 `.private_key`: [`builder.py#L153`](https://github.com/Polymarket/py-clob-client/blob/cc1740c11adf0be33590c1ee4976ce8bfd2f37c2/py_clob_client/order_builder/builder.py#L153)
- CLI config 存储 raw key: [`config.rs#L97`](https://github.com/Polymarket/polymarket-cli/blob/3ba646be1effb0aa7270db481976fcaf16634f5d/src/config.rs#L97)

### Coinbase AgentKit DeFi Actions
- Aave V3 ActionProvider: [`aave_action_provider.py`](https://github.com/coinbase/agentkit/blob/b7b0a7bb121fbfeb0ba1f315fe6663b0b0d946fc/python/coinbase-agentkit/coinbase_agentkit/action_providers/aave/aave_action_provider.py)
- Morpho ActionProvider: [`morpho_action_provider.py`](https://github.com/coinbase/agentkit/blob/b7b0a7bb121fbfeb0ba1f315fe6663b0b0d946fc/python/coinbase-agentkit/coinbase_agentkit/action_providers/morpho/morpho_action_provider.py)
- CDP Swap 网络限制: [`cdp_evm_wallet_action_provider.py`](https://github.com/coinbase/agentkit/blob/main/python/coinbase-agentkit/coinbase_agentkit/action_providers/cdp/cdp_evm_wallet_action_provider.py)

### BNB Chain MCP
- `write_contract` tool: [`tools.ts`](https://github.com/bnb-chain/bnbchain-mcp/blob/43018c3a0819c80283bc90d0641961a94de548b5/src/evm/modules/contracts/tools.ts)
- Swap coming soon: [README](https://github.com/bnb-chain/bnbchain-mcp)
