---
title: 'ISSUE-014: Crossmint vs Coinbase 竞争力对比可视化'
concepts:
- dashboard
- competitive-intelligence
- data-visualization
---
# ISSUE-014: Crossmint vs Coinbase 竞争力对比可视化

## Meta
- **Status**: OPEN
- **Priority**: P2
- **Component**: web/app.js, web/style.css
- **Owner**: TBD
- **Date**: 2026-03-07
- **Effort**: Short (~2-4h)
- **Blocked By**: 建议 1 完成（Crossmint 精准采集上线，`trackable: true`）
- **Blocks**: 无

## Background

ISSUE-012 Phase 4 确认 Crossmint 可精准归因（factory + bundler），采集脚本已升级。
现在 Coinbase 和 Crossmint 两家都有高置信度的链上数据，可以做直接对比。
当前 Dashboard Market Tab 仅展示数字表格和单独的趋势线，缺少竞品之间的对比视角。

## 目标

在 Market Tab 的链上数据卡片中增加竞争力对比视角，帮助 PM 直观判断两家的相对实力和趋势。

## 任务分解

### Task 1: 并排 30d 新增钱包对比图

在现有日级趋势图基础上，增加 Coinbase vs Crossmint 的双线对比视图：
- X 轴：日期（30d）
- Y 轴：当日新增钱包数
- 两条线：Coinbase total / Crossmint precise
- 可选 toggle：显示/隐藏各线

### Task 2: 链偏好分析

Crossmint bundler 已确认多链活跃（Base 642K / Arbitrum 21K / Optimism 5K nonce）。
展示各供应商的链分布饼图或横条图：
- Coinbase：Base vs Ethereum vs 其他
- Crossmint：Base vs Arbitrum vs Optimism

> 注：需要 `collect_market_data.py` 按链分别采集，当前仅采集 `chain=all` 聚合数据。

### Task 3: 增长率对比指标

在表格中增加列或 tooltip：
- 7d 环比增长率（本周 vs 上周）
- 30d 趋势方向（上升/持平/下降）

## 成功标准

- [ ] Dashboard 有 Coinbase vs Crossmint 的双线对比图
- [ ] 增长率指标可见
- [ ] 链偏好分析至少有文字展示（图表为 nice-to-have）

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Crossmint 精准数据量级太小，对比无意义 | 图表视觉不均衡 | 使用对数刻度或双 Y 轴 |
| 按链采集增加 RPC 调用量 | 采集时间变长 | 先做 Base 单链对比，后续扩展 |
