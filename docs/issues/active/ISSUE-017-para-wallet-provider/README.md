---
title: 'ISSUE-017: 新增 Para Wallet Provider — 纯 MPC 钱包基础设施'
concepts:
- wallet
- mpc
- key-sharding
- multi-chain
- signing
---
# ISSUE-017: 新增 Para Wallet Provider — 纯 MPC 钱包基础设施

## Meta
- **Status**: DONE
- **Priority**: P1
- **Component**: adapters/, providers/, runner.py, web/
- **Owner**: TBD
- **Date**: 2026-03-07
- **Effort**: Medium (~4-6h)
- **Blocked By**: 无
- **Blocks**: 无
- **Source**: [openclaw/skills — adeets-22/para-wallet](https://github.com/openclaw/skills/tree/main/skills/adeets-22/para-wallet)

## Background

Para Wallet 是一个纯 MPC 钱包基础设施 Skill，私钥分片永不聚合。唯一同时覆盖 EVM + Solana + Cosmos 三种链族的 Skill。API 极简（3 个端点），与 Privy (TEE + Key Sharding) 直接竞品。

### 核心特性

| 字段 | 内容 |
|------|------|
| 架构 | MPC — 私钥分片，永不聚合 |
| 支持链 | EVM / Solana / Cosmos（三种链族） |
| 钱包能力 | 钱包创建（异步，需轮询状态）、Raw 签名（hex 数据） |
| DeFi 能力 | 无内置 DeFi 工具（纯基础设施） |
| 治理能力 | 无策略引擎 |
| API 端点 | `POST /v1/wallets`（创建）、`GET /v1/wallets/{id}`（状态）、`POST /v1/wallets/{id}/sign-raw`（签名） |

### 关键注意

- **无 `send_transaction`** — 签完名后需自行广播。adapter 需要补 RPC 广播逻辑（参考 BNB Chain MCP 模式）
- **异步创建** — `create_wallet()` 返回后需轮询 `GET /v1/wallets/{id}` 等待状态变为 `ready`
- **应加入** `NO_BUILTIN_APP_PROVIDERS`（无内置 DeFi 能力）

### 与现有 Provider 对比

- vs **Privy**: 同为 MPC/分片架构，但 Privy 有 TEE 加持 + 策略引擎；Para 更纯粹
- vs **BNB Chain MCP**: BNB 是本地私钥；Para 是 MPC 分片，安全模型不同
- vs **OKX OnchainOS**: OKX 是查询网关不签名；Para 是签名基础设施不做查询

## 实施步骤

### Step 1: 调研 Para Wallet API
- [x] 确认 API 端点和认证方式
- [x] 测试钱包创建→轮询→签名流程
- [x] 确认支持的链和签名格式

### Step 2: 创建 `providers/para_wallet.yaml`
- [x] `class: mpc`
- [x] `custody_model: MPC-Shard`
- [x] `chains: [ethereum, solana, cosmos]`
- [x] `signing_modes: [raw_tx, personal_sign]`

### Step 3: 创建 `adapters/para_wallet.py`
- [x] `create_wallet()` — 异步创建 + 轮询等待
- [x] `sign_message()` — `POST /v1/wallets/{id}/sign-raw`
- [x] `sign_typed_data()` — 不支持（标记 UNSUPPORTED）
- [x] `send_transaction()` — 签名后通过公共 RPC 广播
- [x] `capabilities()` — 标注 `token_swap: False`

### Step 4: 编辑 config / runner / dashboard
- [x] 加入 `NO_BUILTIN_APP_PROVIDERS`（无内置 app 能力）
- [x] config.yaml / config.example.yaml 新增配置段
- [x] runner.py / web/app.js 更新

### Step 5: 运行测试并同步结果

## 预期测试结果

| 测试 | 预期 | 原因 |
|------|------|------|
| t01 key_generate | PASS | MPC 钱包创建（异步+轮询） |
| t02 sign_message | PASS | sign-raw API |
| t04 send_tx | PASS | 签名+RPC 广播 |
| t05 multi_chain | PASS | 3 链族 |
| t14 token_swap | N/A | category_mismatch (NO_BUILTIN_APP) |
| app 维度 | 全部 N/A | 纯基础设施 |

## 涉及文件清单

| 操作 | 文件 |
|------|------|
| CREATE | `providers/para_wallet.yaml` |
| CREATE | `adapters/para_wallet.py` |
| CREATE | `evaluations/para_wallet.yaml` |
| EDIT | `config.yaml`, `config.example.yaml` |
| EDIT | `runner.py` |
| EDIT | `web/app.js`, `scripts/collect_market_data.py` |

## 实施结果

- **测试分数**: 27.6%（8 pass，11 fail，9 error）
- **凭证**: Secret Key `sk_beta_*`（非 Client Key `beta_*`）
- **开发者门户**: https://developer.getpara.com（非 dashboard.getpara.com）
- **适配器修复 (ISSUE-022)**:
  1. 修复 hex 编码（`send_transaction` 的 `"0x"` 导致 400）
  2. 添加 500 重试逻辑
  3. 签名作为 tx_hash 返回
- **已知限制**: API 极慢（~20s/请求）、`sign_message` 频繁 500 Internal Server Error，为 Para API 服务端问题
- **Tier**: `openclaw_skill`
