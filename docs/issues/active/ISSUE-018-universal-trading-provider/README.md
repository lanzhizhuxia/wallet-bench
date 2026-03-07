---
title: 'ISSUE-018: 新增 Universal Trading Provider — Particle Network 跨链交易'
concepts:
- wallet
- universal-account
- particle-network
- cross-chain
- dex-swap
- solana
- mev
---
# ISSUE-018: 新增 Universal Trading Provider — Particle Network 跨链交易

## Meta
- **Status**: DONE
- **Priority**: P2
- **Component**: adapters/, providers/, runner.py, web/
- **Owner**: TBD
- **Date**: 2026-03-07
- **Effort**: Medium-High (~6-10h)
- **Blocked By**: 无
- **Blocks**: 无
- **Source**: [openclaw/skills — 0xmomo-ngclubs/universal-trading](https://github.com/openclaw/skills/tree/main/skills/0xmomo-ngclubs/universal-trading)

## Background

Universal Trading 是基于 Particle Network SDK 封装的跨链交易 Skill，覆盖 Solana + EVM (Polygon, Arbitrum, Optimism, BSC, Ethereum)。内置 Buy/Sell/Swap/Transfer + WebSocket 实时监控 + Solana MEV Tip (Jito)。

### 核心特性

| 字段 | 内容 |
|------|------|
| 架构 | Universal Account — Particle Network SDK 封装 |
| 支持链 | Solana + EVM (Polygon, Arbitrum, Optimism, BSC, Ethereum) |
| 钱包能力 | 钱包创建 / 导入、私钥管理（存 .env） |
| DeFi 能力 | Buy / Sell / Swap (Convert) / Transfer、余额查询、WebSocket 实时监控、Slippage 管理、Solana MEV Tip (Jito) |
| 治理能力 | 无 |
| 独特价值 | 跨链交易覆盖最广、支持 Solana MEV 小费、可与 UniversalX 前端互操作 |

### 注意事项

- 依赖 Particle Network 的 Universal Account SDK，稳定性和文档质量需实际验证
- 私钥存 .env（`class: local`），安全模型简单
- **不加入** `NO_BUILTIN_APP_PROVIDERS`（有内置 Swap/Trading 能力）

### 与现有 Provider 对比

- vs **OKX OnchainOS**: 两者都覆盖多链，但 OKX 是查询+报价网关，Universal Trading 是执行方案
- vs **Coinbase AgentKit**: Coinbase 有内置 DeFi action；Universal Trading 有 Solana MEV 保护
- vs **MoonPay**: MoonPay 10 链但无自定义 calldata；Universal Trading 覆盖面更窄但执行能力更强

## 实施步骤

### Step 1: 调研 Universal Trading 安装和接口
- [x] 克隆仓库，理解依赖和配置
- [x] 确认是 Node.js SDK 集成模式（TypeScript warmup.ts）
- [x] 测试 Swap / Transfer 核心流程
- [x] 评估 Particle Network SDK 的稳定性（已验证）

### Step 2: 创建 `providers/universal_trading.yaml`
- [x] `class: local`
- [x] `chains: [ethereum, bsc, polygon, arbitrum, optimism, solana]`
- [x] 配置 Particle Network 凭证（仅需 PROJECT_ID）

### Step 3: 创建 `adapters/universal_trading.py`
- [x] `create_wallet()` — 运行 warmup.ts 获取 UA 地址
- [x] `send_transaction()` — 交易提交 + transactionId 解析
- [x] `token_swap()` — Swap/Convert 功能
- [x] WebSocket 监控（如适用于 t20 tx_confirmation）

### Step 4: 编辑 config / runner / dashboard

### Step 5: 运行测试并同步结果

## 预期测试亮点

| 测试 | 预期 | 原因 |
|------|------|------|
| t01 key_generate | PASS | 钱包创建/导入 |
| t04 send_tx | PASS | 交易提交 |
| t05 multi_chain | PASS | 6+ 链 |
| t14 token_swap | PASS | 内置 Swap |
| t16 cross_chain_bridge | 可能 PASS | Universal Account 跨链能力 |

## 涉及文件清单

| 操作 | 文件 |
|------|------|
| CREATE | `providers/universal_trading.yaml` |
| CREATE | `adapters/universal_trading.py` |
| CREATE | `evaluations/universal_trading.yaml` |
| EDIT | `config.yaml`, `config.example.yaml` |
| EDIT | `runner.py` |
| EDIT | `web/app.js`, `scripts/collect_market_data.py` |

## 实施结果

- **测试分数**: 50.0%（18 pass，7 fail，0 error）—— 适配器修复后从 33.3% 提升到 50.0%
- **凭证**: Particle `PROJECT_ID`（不需要 `CLIENT_KEY`/`APP_ID`）
- **UA 智能合约地址**: `0x210f7148a775600b7AE8B42f805BD63d6779e614`
- **适配器修复 (ISSUE-022)**:
  1. `create_wallet` 通过运行 `warmup.ts` 获取 UA 地址（而非从 `.env` 读取）
  2. 添加 `transactionId` 解析
  3. 地址缓存: `.ua_address` 文件 + env var 读取
- **仓库已克隆**: `./universal-account-example/`
- **Tier**: `openclaw_skill`
