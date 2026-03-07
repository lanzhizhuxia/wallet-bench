---
title: 'ISSUE-019: 新增 Polymarket Agent Provider — 预测市场垂直场景验证'
concepts:
- prediction-market
- polymarket
- polygon
- vertical
---
# ISSUE-019: 新增 Polymarket Agent Provider — 预测市场垂直场景验证

## Meta
- **Status**: DONE
- **Priority**: P3 (垂直场景，可选)
- **Component**: adapters/, providers/
- **Owner**: TBD
- **Date**: 2026-03-07
- **Effort**: Low-Medium (~3-5h)
- **Blocked By**: 无
- **Blocks**: 无
- **Source**: [openclaw/skills — andretuta/polymarket-agent](https://github.com/openclaw/skills/tree/main/skills/andretuta/polymarket-agent)

## Background

Polymarket Agent 是一个预测市场交易 Skill，支持 Polymarket 平台的买/卖/市场扫描/概率分析/自动策略。运行在 Polygon 链上，使用 USDC 结算。

主要评估价值：验证 t17 (prediction_market) 测试项的真实可行性。目前 7 个 Provider 中无一通过 t17。

### 核心特性

| 字段 | 内容 |
|------|------|
| 作者 | andretuta |
| 能力 | Polymarket 预测市场交易（买/卖）、市场扫描、概率分析、自动策略 |
| 链 | Polygon (USDC) |
| 评估价值 | 验证 t17 (prediction_market) 测试项的真实可行性 |

## 实施步骤

### Step 1: 调研 Polymarket Agent 接口
- [x] 确认安装方式和依赖
- [x] 确认 API/CLI 交互模式
- [x] 测试市场查询和模拟下注流程

### Step 2: 创建 provider + adapter
- [x] `providers/polymarket_agent.yaml`
- [x] `adapters/polymarket_agent.py`
- [x] 重点实现 prediction_market 相关方法

### Step 3: 运行测试
- [x] 重点验证 t17 (prediction_market) 是否 PASS

## 预期测试结果

| 测试 | 预期 | 原因 |
|------|------|------|
| t17 prediction_market | PASS | 核心验证目标 |
| t01 key_generate | PASS | 需要钱包来交易 |
| 其他 wallet_core | 取决于底层钱包实现 | |

## 涉及文件清单

| 操作 | 文件 |
|------|------|
| CREATE | `providers/polymarket_agent.yaml` |
| CREATE | `adapters/polymarket_agent.py` |
| EDIT | `config.yaml`, `config.example.yaml`, `runner.py`, `web/app.js` |

## 实施结果

- **测试分数**: 39.3%（11 pass，1 fail，0 error）
- **安装方式**: Homebrew（`brew install polymarket/tap/polymarket`）而非 pip
- **CLI 命令**: `polymarket`（非 `poly`）
- **钱包导入**: `polymarket wallet import <KEY> --signature-type eoa`
- **配置文件**: `~/.config/polymarket/config.json`
- **Tier**: `openclaw_skill`
