---
title: 'ISSUE-016: 新增 Clawlett Provider — Smart Account (Gnosis Safe + Zodiac Roles)'
concepts:
- wallet
- smart-account
- gnosis-safe
- zodiac-roles
- governance
- dex-swap
- mev-protection
---
# ISSUE-016: 新增 Clawlett Provider — Smart Account (Gnosis Safe + Zodiac Roles)

## Meta
- **Status**: DONE
- **Priority**: P0
- **Component**: adapters/, providers/, runner.py, web/
- **Owner**: TBD
- **Date**: 2026-03-07
- **Effort**: Medium (~4-8h)
- **Blocked By**: 无
- **Blocks**: 无
- **Source**: [openclaw/skills — 0xardi/clawlett](https://github.com/openclaw/skills/tree/main/skills/0xardi/clawlett)

## Background

Clawlett 是一个 Smart Account (AA) 架构的钱包 Skill，基于 Gnosis Safe + Zodiac Roles 权限模块。目前 wallet-bench 的 7 个 Provider 中没有 Smart Account 原生架构 + 细粒度权限引擎的组合，Clawlett 填补这个空缺。

### 核心特性

| 字段 | 内容 |
|------|------|
| 架构 | Smart Account (AA) — Gnosis Safe + Zodiac Roles |
| 支持链 | Base Mainnet (Chain ID 8453) |
| 钱包能力 | Safe 合约钱包部署、Zodiac Roles 范围签名、交易提交（受权限约束） |
| DeFi 能力 | DEX Swap（KyberSwap 聚合器 + CoW Protocol MEV 保护）、ETH ⇄ WETH Wrap/Unwrap、ERC-20 Approve |
| 治理能力 | Zodiac Roles 引擎限制 Agent 只能调用白名单合约和函数，Agent 无法提现 |
| 独特价值 | 唯一具备 MEV 保护（CoW Protocol）的 Provider，补充 governance 维度评测 |

### 与现有 Provider 对比

- vs **Privy**: Privy 有策略引擎但基于 TEE；Clawlett 基于合约级权限（Zodiac Roles），链上可验证
- vs **Minara**: Minara 是 MPC+AA 但权限粗粒度；Clawlett 权限模型精细到函数级
- vs **OKX OnchainOS**: OKX 是查询网关；Clawlett 是签名+执行方案

## 实施步骤

### Step 1: 调研 Clawlett CLI/SDK 接口
- [x] 克隆 `0xardi/clawlett` 仓库，理解安装和配置流程
- [x] 确认 CLI 命令清单和参数格式
- [x] 确认 Zodiac Roles 配置方式

### Step 2: 创建 `providers/clawlett.yaml`
- [x] `class: smart_account`
- [x] `custody_model: Smart-Account`
- [x] `chains: [base]`
- [x] `skill.integration_type:` CLI

### Step 3: 创建 `adapters/clawlett.py`
- [x] 实现 WalletAdapter 接口
- [x] `create_wallet()` — Safe 钱包部署
- [x] `sign_message()` / `sign_typed_data()` — 通过 Zodiac Roles 签名
- [x] `send_transaction()` — 受权限约束的交易提交
- [x] `token_swap()` — KyberSwap / CoW Protocol Swap
- [x] `capabilities()` — 重点标注 `policy_enforcement: True`

### Step 4: 编辑 config / runner / dashboard
- [x] config.yaml / config.example.yaml 新增配置段
- [x] runner.py `_load_adapter()` 新增分支
- [x] web/app.js 新增颜色、AI Insight、Market Provider

### Step 5: 运行测试并同步结果
- [x] `python runner.py run --provider clawlett --config config.yaml`
- [x] 同步 `results/public_results.json → web/data/public_results.json`
- [x] 创建 `evaluations/clawlett.yaml`

## 预期测试亮点

| 测试 | 预期 | 原因 |
|------|------|------|
| t01 key_generate | PASS | Safe 钱包部署 |
| t02 sign_message | PASS 或 UNSUPPORTED | 取决于 Zodiac Roles 是否暴露 personal_sign |
| t04 send_tx | PASS | 受权限约束的交易提交 |
| t07 session_delegation | PASS | Zodiac Roles = 原生会话授权 |
| t14 token_swap | PASS | KyberSwap + CoW Protocol |
| governance 维度 | 多项 PASS | Zodiac Roles 引擎 |

## 涉及文件清单

| 操作 | 文件 |
|------|------|
| CREATE | `providers/clawlett.yaml` |
| CREATE | `adapters/clawlett.py` |
| CREATE | `evaluations/clawlett.yaml` |
| EDIT | `config.yaml`, `config.example.yaml` |
| EDIT | `runner.py` |
| EDIT | `web/app.js` |
| EDIT | `web/data/public_results.json` |
| EDIT | `scripts/collect_market_data.py` |

## 实施结果

- **测试分数**: 6.1%（2 pass，6 fail，14 error）
- **根因**: 用户缺少 Base 主网 ETH，无法部署 Gnosis Safe。`config.yaml` 中 `safe_address`/`agent_key`/`owner_address` 为占位符，未配置真实凭证。
- **Tier**: 重分类为 `openclaw_skill`（非 `waas_infrastructure`）
- **仓库已克隆**: `./clawlett/`
