---
title: 'ISSUE-020: 新增 Coinpilot Hyperliquid Provider — 永续合约垂直场景验证'
concepts:
- perps-trading
- hyperliquid
- copy-trade
- vertical
---
# ISSUE-020: 新增 Coinpilot Hyperliquid Provider — 永续合约垂直场景验证

## Meta
- **Status**: DONE
- **Priority**: P3 (垂直场景，可选)
- **Component**: adapters/, providers/
- **Owner**: TBD
- **Date**: 2026-03-07
- **Effort**: Low-Medium (~3-5h)
- **Blocked By**: 无
- **Blocks**: 无
- **Source**: [openclaw/skills — alannkl/coinpilot-hyperliquid-copy-trade](https://github.com/openclaw/skills/tree/main/skills/alannkl/coinpilot-hyperliquid-copy-trade)

## Background

Coinpilot Hyperliquid Copy Trade 是一个永续合约跟单交易 Skill，支持多钱包管理和风控参数配置，运行在 Hyperliquid L1 上。

主要评估价值：验证 t18 (perps_trading) 测试项的真实可行性。目前 7 个 Provider 中无一通过 t18。

### 核心特性

| 字段 | 内容 |
|------|------|
| 作者 | alannkl |
| 能力 | 永续合约跟单交易、多钱包管理、风控参数配置 |
| 链 | Hyperliquid (L1) |
| 评估价值 | 验证 t18 (perps_trading) 测试项的真实可行性 |

## 实施步骤

### Step 1: 调研 Coinpilot 接口
- [x] 确认安装方式和依赖
- [x] 确认 Hyperliquid API 交互方式
- [x] 测试跟单和风控配置流程

### Step 2: 创建 provider + adapter
- [x] `providers/coinpilot_hyperliquid.yaml`
- [x] `adapters/coinpilot_hyperliquid.py`
- [x] 重点实现 perps_trading 相关方法

### Step 3: 运行测试
- [x] 重点验证 t18 (perps_trading) 是否 PASS

## 预期测试结果

| 测试 | 预期 | 原因 |
|------|------|------|
| t18 perps_trading | PASS | 核心验证目标 |
| t01 key_generate | PASS | 需要钱包来交易 |
| 其他 wallet_core | 取决于底层钱包实现 | |

## 涉及文件清单

| 操作 | 文件 |
|------|------|
| CREATE | `providers/coinpilot_hyperliquid.yaml` |
| CREATE | `adapters/coinpilot_hyperliquid.py` |
| EDIT | `config.yaml`, `config.example.yaml`, `runner.py`, `web/app.js` |

## 实施结果

- **测试分数**: 12.0%（3 pass，6 fail，0 error）
- **重大发现**: Coinpilot 是纯移动端 App（iOS/Android），网址为 trycoinpilot.com（非 coinpilot.ai）。无公开开发者 API、无 CLI、无 Web 注册入口。无法配置凭证。
- **Tier**: `openclaw_skill`
