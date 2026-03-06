---
title: 'ISSUE-007: 基础能力细分 — 钱包基础/权限治理/稳定性/运维能力四维度'
concepts:
- test-taxonomy
- infra-sub-dimensions
- filter-ux
---
# ISSUE-007: 基础能力细分 — 钱包基础/权限治理/稳定性/运维能力四维度

## Meta
- **Status**: OPEN
- **Priority**: P2
- **Component**: wallet-bench / web (app.js + style.css)
- **Owner**: —
- **Date**: 2026-03-05
- **Effort**: Low (< 0.5d)
- **Depends**: ISSUE-006（测试分类重构完成后实施）
- **Source**: 用户反馈 — "基础能力里有些跟权限相关的，跟钱包本身功能不相关，能否再拆"

## Background

ISSUE-006 将 21 个测试分为"基础能力 (13)"和"应用能力 (5)"两大类。但基础能力内部混杂了不同关注点：

- 钱包本身能做什么（创建、签名、转账）
- 谁能用、怎么管（策略、授权、审计）
- 压力下表现如何（并发、故障恢复、限流）
- 日常运维（迁移、备份）

PM 在筛选时无法快速定位"我只关心权限治理"或"我只关心稳定性"。

## 核心目标

将原有的"基础能力"一级分类细分为 4 个子维度，让筛选器和矩阵表的分组更精确。

## 维度定义

| 子维度 | 中文标签 | category 值 | 包含测试 (test_name) |
|--------|---------|-------------|---------------------|
| 核心钱包 | 钱包基础 | `wallet_core` | key_generate, sign_message, sign_typed_data, send_tx, multi_chain, preflight_fee |
| 治理与权限 | 权限治理 | `governance` | policy_enforcement, session_delegation, authorization_audit_trace |
| 可靠性 | 稳定性 | `reliability` | concurrent_ops, failure_recovery, rate_limit_resilience |
| 可运维性 | 运维能力 | `ops` | portability_recovery + 架构特定 tc01-tc03（derivation_path, keychain_lock, backup_recovery 等） |
| 应用层 | 应用能力 | `app` | token_swap, defi_interaction, cross_chain_bridge, prediction_market, perps_trading |

## Acceptance Criteria

### AC-007-1: TEST_CATEGORY 常量更新
将 `app.js` 中 `TEST_CATEGORY` 的 `'infra'` 值替换为具体子维度：

```javascript
const TEST_CATEGORY = {
    // 钱包基础 (wallet_core)
    key_generate: 'wallet_core',
    sign_message: 'wallet_core',
    sign_typed_data: 'wallet_core',
    send_tx: 'wallet_core',
    multi_chain: 'wallet_core',
    preflight_fee: 'wallet_core',
    // 权限治理 (governance)
    policy_enforcement: 'governance',
    session_delegation: 'governance',
    authorization_audit_trace: 'governance',
    // 稳定性 (reliability)
    concurrent_ops: 'reliability',
    failure_recovery: 'reliability',
    rate_limit_resilience: 'reliability',
    // 运维能力 (ops) — shared tests
    portability_recovery: 'ops',
    // 运维能力 (ops) — arch-specific tests
    derivation_path: 'ops',
    keychain_lock: 'ops',
    backup_recovery: 'ops',
    intent_schema: 'ops',
    fulfillment_sla: 'ops',
    cancellation: 'ops',
    attestation: 'ops',
    failover_continuity: 'ops',
    policy_depth: 'ops',
    // 应用能力 (app)
    token_swap: 'app',
    defi_interaction: 'app',
    cross_chain_bridge: 'app',
    prediction_market: 'app',
    perps_trading: 'app',
};
```

### AC-007-2: runner.py TEST_CATEGORY 同步更新
`runner.py` 中的 `TEST_CATEGORY` 字典同步更新为相同的 5 分类值（wallet_core / governance / reliability / ops / app）。`_is_not_applicable()` 逻辑需适配：infra provider 的 `app` 类测试仍为 N/A，其余子维度不受影响。

### AC-007-3: 筛选器 Tab 更新
第一层类别 Tab 从 3 个扩展为 6 个：

```
全部 (N) | 钱包基础 (6) | 权限治理 (3) | 稳定性 (3) | 运维能力 (1+tc) | 应用能力 (5)
```

- 点击类别 Tab 过滤下方功能 pills 的可见范围
- 数字为该类别的测试数量（动态计算）
- 默认选中"全部"
- pills 的 `data-cat` 属性更新为新的 category 值

### AC-007-4: 矩阵表分组标题更新
矩阵表的分组行标题从 2 个（"基础能力"/"应用能力"）扩展为 5 个：

- 钱包基础
- 权限治理
- 稳定性
- 运维能力
- 应用能力

分组顺序按上述排列，每组内测试按 test_id 排序。

### AC-007-5: 详情页测试表分组
详情页测试结果表的分组/排序逻辑同步更新，按 5 个维度分组。

### AC-007-6: N/A 逻辑不变
`getApplicableResults()`、`computeRadarScores()`、`renderDecisionBar()` 等的 N/A 排除逻辑不受影响 — 仍基于 `status === 'not_applicable'` 判断，与 category 值无关。

### AC-007-7: 向后兼容
`provider_type` 字段（infra / app_toolkit）保持不变。`_is_not_applicable()` 在 runner.py 中判断 app 测试时使用 `category == 'app'`（不变）。

## EXIT Gate

- [ ] TEST_CATEGORY 使用 5 个子维度值（wallet_core / governance / reliability / ops / app）
- [ ] runner.py TEST_CATEGORY 同步更新
- [ ] 筛选器显示 6 个 Tab（含"全部"）
- [ ] 矩阵表有 5 个分组行标题
- [ ] 详情页测试表按 5 维度分组
- [ ] N/A 评分逻辑不受影响
- [ ] 0 JS error
- [ ] `node -c web/app.js` 通过
- [ ] `python3 -c "import ast; ast.parse(open('runner.py').read())"` 通过

## Execution Log

| 日期 | 事件 | 详情 |
|------|------|------|
| 2026-03-05 | 发现 | 用户反馈基础能力内有权限相关测试与钱包功能不相关 |
| 2026-03-05 | Issue 创建 | 5 子维度 + 7 AC + EXIT Gate |
