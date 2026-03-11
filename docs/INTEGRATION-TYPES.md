# AI Agent 钱包集成方式对比

**日期**: 2026-03-05
**适用**: wallet-bench 所有 provider

---

## 为什么集成方式很重要？

对 AI Agent 而言，钱包的**集成方式**决定了：

- **接入成本** — 需要写多少代码才能让 Agent 调用钱包？
- **可靠性** — Agent 调用是否有类型安全、schema 校验？
- **可移植性** — 能否跨 Agent 框架（Claude、LangChain、AutoGen）复用？
- **发现性** — Agent 能否自动发现钱包的能力（tool list），还是需要人写 prompt？

选错集成方式，可能意味着 **3 天的适配工作** vs **3 分钟的 npx 启动**。

---

## 六种集成方式一览

| 排序 | 集成方式 | Agent 友好度 | 代表 Provider |
|:---:|---|:---:|---|
| 1 | **MCP Server** | ⭐⭐⭐⭐⭐ | Privy, BNB Chain MCP, Crossmint (checkout) |
| 2 | **OpenClaw Plugin** | ⭐⭐⭐⭐ | Crossmint (lobster.cash) |
| 3 | **Python/TS SDK** | ⭐⭐⭐½ | Coinbase AgentKit |
| 4 | **CLI Subprocess** | ⭐⭐⭐ | MoonPay, Minara |
| 5 | **SKILL.md (Prompt 注入)** | ⭐⭐½ | Privy (OpenClaw Skill) |
| 6 | **REST API** | ⭐⭐ | (各家的底层 API) |

---

## 1. MCP Server（最优）

```
Agent ←stdio→ MCP Server ←HTTP→ Provider API
```

**Model Context Protocol (MCP)** 是 Anthropic 于 2024 年提出的开放协议，定义了 AI Agent 与外部工具之间的标准通信方式。

### 为什么最好

| 优势 | 说明 |
|---|---|
| **协议标准化** | tool name、参数 schema（Zod/JSON Schema）、返回格式全部 typed，Agent 不需要"猜"怎么调用 |
| **零代码集成** | `npx @privy-io/mcp-server` 或 `npx @bnb-chain/mcp` 即用 |
| **双向通信** | Server 可主动推送 progress、log，不只是 request-response |
| **跨框架复用** | Claude Desktop、Cursor、Claude Code、LangChain、AutoGen 都原生支持 |
| **自动发现** | Agent 调用 `list_tools()` 即可获取所有可用工具和参数定义 |

### 局限

- 进程常驻（stdio transport），多 provider 并行时占资源
- 如果 MCP Server 非官方出品，质量可能参差不齐
- 仍需 API 凭证（App ID / Secret / Private Key）

### 实际示例

**Privy MCP Server** — 25+ typed tools：

```json
{
  "mcpServers": {
    "privy": {
      "command": "npx",
      "args": ["@privy-io/mcp-server"],
      "env": {
        "PRIVY_APP_ID": "your-app-id",
        "PRIVY_APP_SECRET": "your-app-secret"
      }
    }
  }
}
```

Agent 自动获得 `create_wallet`、`personal_sign`、`eth_sendTransaction`、`create_policy` 等工具，无需手写任何 adapter。

**BNB Chain MCP** — BSC/opBNB 链上操作：

```json
{
  "mcpServers": {
    "bnbchain": {
      "command": "npx",
      "args": ["-y", "@bnb-chain/mcp"],
      "env": {
        "PRIVATE_KEY": "0x..."
      }
    }
  }
}
```

---

## 2. OpenClaw Plugin

```
Agent (OpenClaw daemon) ←in-process→ Plugin Runtime ←HTTP→ Provider API
```

OpenClaw 是 2026 年最流行的开源 AI Agent 框架（264k+ GitHub Stars），其插件系统允许 npm 包直接注入 Agent 运行时。

### 特点

| 优势 | 局限 |
|---|---|
| 类 MCP 的 typed 体验 | **锁死在 OpenClaw 生态** |
| npm install 即用 | 不兼容 Claude Desktop / LangChain |
| 进程内执行，低延迟 | 插件安全性依赖 OpenClaw 审核 |
| 可共享本地密钥存储 | 生态较新，插件数量有限 |

### 实际示例

**lobster.cash** — Crossmint 的 OpenClaw 支付插件：

```bash
openclaw plugins install @crossmint/lobster.cash
```

独特之处：
- 本地 ed25519 密钥 + 委托签名（Agent 密钥不出机）
- **Visa 虚拟信用卡**（Agent 可以在法币世界消费）
- **x402 支付协议**（HTTP 402 自动付款）
- Solana USDC 链上支付

这意味着 Agent 不仅能做链上交易，还能**刷信用卡购物** — 这是纯 REST API 集成无法覆盖的能力维度。

---

## 3. Python / TypeScript SDK

```
Agent ←function call→ SDK (typed) ←HTTP→ Provider API
```

### 特点

| 优势 | 局限 |
|---|---|
| 完整类型安全（Pydantic / TypeScript） | 需要写代码，管理依赖 |
| 同步调用，错误处理清晰 | 绑定特定语言 |
| IDE 补全、调试友好 | 无自动 tool 发现（需人写 wrapper） |

### 实际示例

**Coinbase AgentKit** — Python SDK：

```python
from coinbase_agentkit import AgentKit, CdpEvmWalletProvider

wallet = CdpEvmWalletProvider(network_id="base-sepolia")
kit = AgentKit(wallet_provider=wallet)

# 类型安全的函数调用
result = kit.run_action("transfer", {
    "amount": "0.001",
    "asset_id": "eth",
    "destination": "0x..."
})
```

SDK 的优势在于 **类型安全和 IDE 体验**，但相比 MCP，Agent 无法自动发现可用工具 — 需要人类开发者写 LangChain Tool wrapper。

---

## 4. CLI Subprocess

```
Agent → subprocess.Popen → `cli-tool --arg1 val1 --json` → parse stdout
```

### 特点

| 优势 | 局限 |
|---|---|
| 安装简单（npm install -g） | 每次调用 fork 新进程，冷启动开销大 |
| 一条命令一个动作，语义清晰 | 输出格式不保证（`--json` 可能不输出 JSON） |
| 不需要理解 HTTP 认证 | 交互式 prompt 会阻塞自动化 |
| 非托管方案，密钥本地 | 错误处理靠 exit code + stderr 文本解析 |

### 实际示例

**MoonPay CLI**：

```bash
mp wallet create --json
# {"address": "0x...", "type": "evm", "chain": "ethereum"}

mp send --to 0x... --amount 0.01 --chain ethereum --json
```

MoonPay 的 `--json` 输出较可靠。但 **Minara 的 `--json` flag 实际不输出 JSON** — 这是 CLI 集成的最大风险：你无法信任 flag 文档，必须实际验证。

### CLI 的特殊问题

1. **交互式 UI 阻塞**：Minara 的 token 选择器弹出 inquirer UI，必须用 `stdin=DEVNULL` 防止卡死
2. **进程管理**：subprocess 需要超时控制、僵尸进程清理
3. **输出解析脆弱**：CLI 输出可能包含 ANSI 颜色码、进度条等干扰字符

---

## 5. SKILL.md（Prompt 注入）

```
Agent ← system prompt injection → SKILL.md (markdown) → Agent 自行调用 REST API
```

### 特点

| 优势 | 局限 |
|---|---|
| **最轻量** — 纯文本文件 | **最不可靠** — 完全靠 LLM 理解力 |
| 无运行时依赖 | 无类型安全，无 schema 校验 |
| 跨 LLM 通用（Claude/GPT/Cursor） | 复杂操作容易"幻觉"（编造参数） |
| 安装到 `~/.openclaw/skills/` | 安全指令可被 prompt injection 绕过 |

### 工作原理

SKILL.md 被注入到 Agent 的 system prompt 中，告诉 Agent "你有以下 REST API 可用"。Agent 读完说明后，**自行构造 HTTP 请求**。

```markdown
## 创建钱包
POST /api/v1/wallets
Headers: Authorization: Basic {base64(APP_ID:APP_SECRET)}
Body: {"chain_type": "ethereum"}
Response: {"id": "wallet_xxx", "address": "0x..."}
```

这本质上是**让 LLM 当 HTTP 客户端** — 能力上限取决于 LLM 对 REST API 的理解。适合简单场景，不适合需要精确参数的链上操作。

---

## 6. REST API（最原始）

```
Agent → 自定义 adapter 代码 → HTTP client → Provider REST API
```

### 特点

| 优势 | 局限 |
|---|---|
| 最灵活，任何语言/框架可用 | 接入成本最高 |
| 完全控制请求/响应 | 需自行处理认证、序列化、重试 |
| 无中间层开销 | Agent 无法自动发现能力 |
| 适合定制化需求 | 每个 provider 的 API 风格不同 |

REST API 是所有其他方式的**底层基础** — MCP Server、SDK、CLI 最终都是在调用 REST API。直接用 REST API 给了最大灵活性，但代价是最高的集成成本。

---

## 综合对比

### 定量评估

| 维度 | MCP | Plugin | SDK | CLI | SKILL.md | REST |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| 接入代码量 | **0 行** | **0 行** | ~50 行 | ~30 行 | **0 行** | ~200 行 |
| 类型安全 | ✅ Zod | ✅ TS | ✅ | ❌ | ❌ | ❌ |
| 自动 tool 发现 | ✅ `list_tools` | ✅ | ❌ | ❌ | ❌ | ❌ |
| 跨框架复用 | ✅ | ❌ OpenClaw only | ❌ 语言绑定 | ✅ | ✅ | ✅ |
| 调用延迟 | ~同 REST | 进程内更低 | ~同 REST | +200ms 进程开销 | ~同 REST | 基准 |
| 出错可追溯性 | ✅ structured | ✅ | ✅ | ⚠️ stderr | ❌ | ⚠️ HTTP code |
| Agent 自主度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | ⭐⭐ |

### 决策树

```
你的 Agent 运行在什么框架上？
├─ OpenClaw → 优先用 Plugin，没有则用 MCP
├─ Claude Desktop / Cursor → 用 MCP
├─ LangChain / AutoGen → 用 MCP 或 SDK
├─ 自建框架 (Python) → 用 SDK，没有则 REST
└─ 自建框架 (其他) → 用 CLI，没有则 REST
```

---

## wallet-bench 中各 Provider 的集成方式

| Provider | 类型 | 主要集成方式 | 替代路径 | 独特能力 |
|---|---|---|---|---|
| **Privy Agentic Wallets** | WaaS | `mcp_server_stdio` (`@privy-io/mcp-server`) | REST API | 策略引擎 + 多签 Quorum |
| **BNB Chain MCP** | WaaS | `mcp_server_stdio` (`@bnb-chain/mcp`) | — | 零注册，毫秒级 |
| **Crossmint Wallets** | WaaS | `mcp_server_stdio` (mcp-crossmint-checkout) | REST API | Visa 虚拟卡 + x402 |
| **MoonPay Agents** | WaaS | `cli_subprocess` (`@moonpay/cli`) | `mp mcp` 转 MCP Server | 54 工具, 10 链 |
| **Coinbase AgentKit** | WaaS | `python_sdk` (`coinbase-agentkit`) | — | 内置 faucet |
| **Minara AI** | WaaS | `cli_subprocess` (`minara`) | — | DeFi 一站式 |
| **OKX OnchainOS** | WaaS | `rest_api` | — | 链聚合器，多链意图执行 |
| **Clawlett** | OpenClaw Skill | `cli_subprocess` (clawlett repo scripts) | — | Gnosis Safe + Zodiac Roles 细粒度权限 |
| **Para Wallet** | OpenClaw Skill | `rest_api` (Para API) | — | MPC 分片密钥，EVM + Solana + Cosmos |
| **Universal Trading** | OpenClaw Skill | `cli_subprocess` (Particle Network SDK) | — | 跨链最广，支持 Solana MEV |
| **Polymarket Agent** | OpenClaw Skill | `cli_subprocess` (`polymarket` CLI) | — | Polymarket CLOB 全链路自动化 |
| **Coinpilot Hyperliquid** | OpenClaw Skill | `cli_subprocess` (coinpilot scripts) | — | Hyperliquid 永续合约跟单 |

---

## 趋势观察

### 2025 → 2026 的变化

```
2025: Provider → REST API → 你的代码调用
2026: Provider → MCP Server / Skill → AI Agent 平台自动发现和调用
```

- **Privy** 从纯 REST API 演化为 MCP Server + OpenClaw Skill
- **Crossmint** 从纯 REST API 演化为 MCP Server + OpenClaw Plugin (lobster.cash)
- **MoonPay** 的 CLI 可通过 `mp mcp` 一键转为 MCP Server
- **MCP 协议**正在成为 AI Agent 工具集成的事实标准

### 对开发者的建议

1. **新项目首选 MCP** — 如果 provider 有官方 MCP Server，不要再手写 REST adapter
2. **评估 provider 时看 `integration_type`** — 这直接决定 Agent 的接入成本
3. **CLI 谨慎信任** — `--json` flag 不等于真的输出 JSON，实际验证不可省略
4. **SKILL.md 适合探索，不适合生产** — 它本质是让 LLM 读说明书自己调 API

---

*本文是 [wallet-bench](/) 项目的一部分。每个 provider 详情页的「Agent Skill 集成信息」section 中的集成方式标签均可跳转至本文。*
