# 下一步计划 — 候选评测对象与未来方向

**日期**: 2026-03-09（更新：ISSUE-028）
**来源**: OpenClaw ClawHub 生态调研（7,300+ Skills 扫描）
**筛选标准**: 具备钱包创建 / 签名 / 链上交易执行能力（排除纯数据查询、纯支付通道）

---

---

## 〇、当前评测状态

| Skill | Tier | 分数 | 状态 |
|-------|------|------|------|
| Clawlett | openclaw_skill | 7.4% | ⚠️ 凭证未配置，结果不代表真实能力 |
| Para Wallet | openclaw_skill | 27.6% | ⚠️ API 不稳定，已纳入评测 |
| Polymarket Agent | openclaw_skill | 39.3% | ✅ 配置正确 |
| Universal Trading | openclaw_skill | 50.0% | ✅ 适配器已修复，已纳入评测 |
| Coinpilot Hyperliquid | openclaw_skill | 12.0% | ❌ 无 API |
|-------|------|------|------|
| Clawlett | openclaw_skill | 6.1% | ❌ 需 Base ETH |
| Para Wallet | openclaw_skill | 27.6% | ⚠️ API 不稳定 |
| Polymarket Agent | openclaw_skill | 39.3% | ✅ 配置正确 |
| Universal Trading | openclaw_skill | 50.0% | ✅ 适配器已修复 |
| Coinpilot Hyperliquid | openclaw_skill | 12.0% | ❌ 无 API |

---

## 一、候选评测对象

### P0 — Clawlett（最优先）

| 字段 | 内容 |
|------|------|
| **名称** | Clawlett |
| **作者** | 0xardi |
| **ClawHub 原始链接** | [openclaw/skills — 0xardi/clawlett](https://github.com/openclaw/skills/tree/main/skills/0xardi/clawlett) |
| **架构类别** | Smart Account (AA) — Gnosis Safe + Zodiac Roles 权限模块 |
| **支持链** | Base Mainnet (Chain ID 8453) |
| **钱包能力** | Safe 合约钱包部署、Zodiac Roles 范围签名、交易提交（受权限约束） |
| **DeFi 能力** | DEX Swap（KyberSwap 聚合器 + CoW Protocol MEV 保护）、ETH ⇄ WETH Wrap/Unwrap、ERC-20 Approve |
| **治理能力** | Zodiac Roles 引擎限制 Agent 只能调用白名单合约和函数，**Agent 无法提现** |
| **独特价值** | 目前 wallet-bench 里唯一能对标的是 Minara (MPC+AA)，但 Clawlett 的权限模型远比 Minara 精细。自带 MEV 保护（CoW Protocol）。正好补充 `governance` 维度评测 |

**推荐理由**: 在已有 6 个 Provider 中，没有一个是 Smart Account 原生架构 + 细粒度权限引擎的组合。Clawlett 填补这个空缺。

---

### P1 — Para Wallet

| 字段 | 内容 |
|------|------|
| **名称** | Para Wallet |
| **作者** | adeets-22 |
| **ClawHub 原始链接** | [openclaw/skills — adeets-22/para-wallet](https://github.com/openclaw/skills/tree/main/skills/adeets-22/para-wallet) |
| **架构类别** | MPC — 私钥分片，永不聚合 |
| **支持链** | EVM / Solana / Cosmos（三种链族） |
| **钱包能力** | 钱包创建（异步，需轮询状态）、Raw 签名（hex 数据） |
| **DeFi 能力** | 无内置 DeFi 工具（纯基础设施） |
| **治理能力** | 无策略引擎 |
| **独特价值** | 纯 MPC 钱包基础设施，与 Privy (TEE + Key Sharding) 直接竞品。**唯一同时覆盖 EVM + Solana + Cosmos 三种链族的 Skill**。API 设计极简（3 个端点） |
| **API 端点** | `POST /v1/wallets`（创建）、`GET /v1/wallets/{id}`（状态）、`POST /v1/wallets/{id}/sign-raw`（签名） |
| **注意** | 无 `send_transaction` 能力 — 签完名后需自行广播。测试时 t04 (send_tx) 需在 adapter 层补广播逻辑 |

**推荐理由**: 最纯粹的 MPC 钱包 Skill，架构透明，适合作为 MPC 类别的标杆参照物。

---

### P2 — Universal Trading (Particle Network)

| 字段 | 内容 |
|------|------|
| **名称** | Universal Trading |
| **作者** | 0xmomo-ngclubs |
| **ClawHub 原始链接** | [openclaw/skills — 0xmomo-ngclubs/universal-trading](https://github.com/openclaw/skills/tree/main/skills/0xmomo-ngclubs/universal-trading) |
| **架构类别** | Universal Account — Particle Network SDK 封装 |
| **支持链** | Solana + EVM (Polygon, Arbitrum, Optimism, BSC, Ethereum) |
| **钱包能力** | 钱包创建 / 导入、私钥管理（存 .env） |
| **DeFi 能力** | Buy / Sell / Swap (Convert) / Transfer、余额查询、WebSocket 实时监控、Slippage 管理、Solana MEV Tip (Jito) |
| **治理能力** | 无 |
| **独特价值** | 跨链交易覆盖最广、支持 Solana MEV 小费、脚本编排可自动化。可与 UniversalX 前端互操作 |
| **注意** | 依赖 Particle Network 的 Universal Account SDK，稳定性和文档质量需实际验证 |

**推荐理由**: 如果扩展评测范围到跨链交易场景，这是最全面的候选。

---

## 二、垂直场景候选（可选关注）

这些 Skill 有链上操作能力，但聚焦于特定垂直场景，视 wallet-bench 范围扩展需求决定是否纳入。

### Polymarket Agent

| 字段 | 内容 |
|------|------|
| **作者** | andretuta |
| **ClawHub 原始链接** | [openclaw/skills — andretuta/polymarket-agent](https://github.com/openclaw/skills/tree/main/skills/andretuta/polymarket-agent) |
| **能力** | Polymarket 预测市场交易（买/卖）、市场扫描、概率分析、自动策略 |
| **链** | Polygon (USDC) |
| **评估价值** | 可用于验证 t17 (prediction_market) 测试项的真实可行性 |

### Coinpilot Hyperliquid Copy Trade

| 字段 | 内容 |
|------|------|
| **作者** | alannkl |
| **ClawHub 原始链接** | [openclaw/skills — alannkl/coinpilot-hyperliquid-copy-trade](https://github.com/openclaw/skills/tree/main/skills/alannkl/coinpilot-hyperliquid-copy-trade) |
| **能力** | 永续合约跟单交易、多钱包管理、风控参数配置 |
| **链** | Hyperliquid (L1) |
| **评估价值** | 可用于验证 t18 (perps_trading) 测试项的真实可行性 |

---

## 三、已排除的项目

| 项目 | 排除理由 |
|------|----------|
| **Claw402** ([claw402.ai](https://claw402.ai/)) | 数据 API 聚合器 + x402 微支付通道。私钥仅用于 USDC 付费，无钱包创建/签名/交易能力 |
| **x402engine** ([openclaw/skills — agentc22/x402engine](https://github.com/openclaw/skills/tree/main/skills/agentc22/x402engine)) | 同上，x402 支付中间层 + 70+ 付费 API 路由。无钱包原语 |
| **ethskills** ([openclaw/skills — austintgriffith/ethskills](https://github.com/openclaw/skills/tree/main/skills/austintgriffith/ethskills)) | 纯知识库（Ethereum 开发文档），不是工具，无任何执行能力 |
| **wallet-api** ([openclaw/skills — andresubri/wallet-api](https://github.com/openclaw/skills/tree/main/skills/andresubri/wallet-api)) | 名字误导 — 实际是 BudgetBakers 个人记账 App 的 API 封装，与 crypto 无关 |
| **Settld MCP Payments** ([openclaw/skills — aidenlippert/settld-mcp-payments](https://github.com/openclaw/skills/tree/main/skills/aidenlippert/settld-mcp-payments)) | 传统 API 计费/收据系统，非区块链项目 |

---

## 四、未来评测维度扩展方向

当前 wallet-bench 覆盖 5 个评测维度（wallet_core / governance / reliability / ops / app）。以下维度在本轮暂不纳入，但值得在后续版本中考虑：

| 候选维度 | 说明 | 触发条件 |
|----------|------|----------|
| **x402 支付协议** | Agent 通过 HTTP 402 自动完成链上微支付的能力 | 当 x402 生态成熟、有 3+ 个可对比的实现时 |
| **Agent 经济自主性** | Agent 自主管理预算、按需付费、成本可控 | 当"Agent 自己赚钱自己花"成为主流需求时 |
| **企业级策略引擎** | 多签、审批流、支出限额、合约白名单 | 当 2+ 个 Provider 提供可测试的策略 API 时（目前仅 Privy 声称支持） |
| **跨链原子操作** | 单次操作跨 2+ 条链完成（如 Bridge + Swap） | 当 Universal Account 类方案稳定可测时 |

---

*本文是 wallet-bench「了解更多 → 下一步计划」子 Tab 的内容来源。*
*调研时间: 2026-03-06 | 调研范围: ClawHub 7,300+ Skills (openclaw/skills repo)*
