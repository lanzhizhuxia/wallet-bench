---
title: 'ISSUE-014: Crossmint vs Coinbase 竞争力对比可视化'
concepts:
- dashboard
- competitive-intelligence
- data-visualization
---
# ISSUE-014: Crossmint vs Coinbase 竞争力对比可视化

## Meta
- **Status**: DONE (Task 1-3 全部完成)
- **Priority**: P2
- **Component**: web/app.js, web/style.css
- **Owner**: TBD
- **Date**: 2026-03-07
- **Effort**: Short (~1-2h 剩余)
- **Blocked By**: ~~建议 1 完成（Crossmint 精准采集上线，`trackable: true`）~~ ✅ 已解除 (ISSUE-012 Phase 4 完成, commit `9f81aa0`)
- **Blocks**: 无

ISSUE-012 Phase 4 确认 Crossmint 可精准归因（factory + bundler），采集脚本已升级。
现在 Coinbase 和 Crossmint 两家都有高置信度的链上数据，可以做直接对比。

**2026-03-07 状态更新**：
- ✅ Crossmint 精准归因已上线 (`_collect_crossmint_precise()` via RPC `eth_getLogs`)
- ✅ Dashboard 已有 30d 日维度趋势图，含 Coinbase total + Crossmint 双线 (`initOnchainDailyChart()`)
- ✅ Chart.js 图例已支持点击显示/隐藏各线（原生 legend toggle）
- ✅ 链偏好分析已实现（Coinbase 按链采集 BundleBear + Crossmint nonce 比例）
- ✅ 7d 环比增长率 badge + 30d 趋势方向已实现

## 目标

在 Market Tab 的链上数据卡片中增加竞争力对比视角，帮助 PM 直观判断两家的相对实力和趋势。

## 任务分解

### Task 1: 并排 30d 新增钱包对比图 ✅ 已完成

> **已由 ISSUE-011 Phase 2 实现** — `initOnchainDailyChart()` (app.js:2840) 已有 4 条线：
> - Coinbase 日新增激活（合计）
> - Coinbase 智能账户 (ERC-4337)
> - Coinbase EOA 授权 (EIP-7702)
> - Crossmint ≈上界
> 
> Chart.js legend 原生支持点击 toggle 显示/隐藏，完全满足 Task 1 需求。

### Task 2: 链偏好分析 ✅ 已完成

Crossmint bundler 已确认多链活跃（Base 642K / Arbitrum 21K / Optimism 5K nonce）。
展示各供应商的链分布堆叠条形图：
- Coinbase：BundleBear 按链采集（base/ethereum/arbitrum/optimism/polygon）
- Crossmint：基于 bundler nonce 累计比例 × 30d 总量

> 实现：`_collect_chain_distribution()` + `renderChainDistribution()` + CSS 水平堆叠条

### Task 3: 增长率对比指标 ✅ 已完成

在表格 30日激活列追加 badge：
- 7d 环比增长率（WoW `computeGrowthMetrics()`）
- 30d 趋势方向（线性回归斜率，阈值 ±2%，up/flat/down 箭头）

## 成功标准

- [x] Dashboard 有 Coinbase vs Crossmint 的双线对比图 ✅ (ISSUE-011 Phase 2 已实现)
- [x] 增长率指标可见 ✅ (7d WoW badge + 30d 趋势箭头)
- [x] 链偏好分析至少有文字展示（图表为 nice-to-have） ✅ (堆叠条形图)

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Crossmint 精准数据量级太小，对比无意义 | 图表视觉不均衡 | 使用对数刻度或双 Y 轴 |
| 按链采集增加 RPC 调用量 | 采集时间变长 | 先做 Base 单链对比，后续扩展 |
