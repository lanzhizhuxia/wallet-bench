---
title: 'ISSUE-009: 功能对比卡片融入 DeFi 场景集成成本（能力+成本 融合视图）'
concepts:
- information-architecture
- feature-comparison
- defi-integration
- decision-support
---
# ISSUE-009: 功能对比卡片融入 DeFi 场景集成成本（能力+成本 融合视图）

## Meta
- **Status**: OPEN
- **Priority**: P1
- **Component**: web/app.js, web/style.css
- **Owner**: —
- **Date**: 2026-03-06
- **Effort**: Small (2-3 hours)
- **Ref**: ISSUE-001 (基础设施), ISSUE-003 (UI polish)
- **GitHub Issue**: #1

## Background

决策者核心关注点：**「用户装上这个钱包能做什么？做这个事情 effort 有多大？」**

当前这两个维度分散在两个 tab：
- **功能对比 (Tab 1)**：展示基础能力 ✅/❌、Key 托管、签名方式、支持链、治理标签 — 偏"测试指标"
- **决策视图 (Tab 5)**：展示 DeFi 场景集成成本热力图（Simple/Medium/Complex/Not Feasible + effort days）— 偏"行动力"

角色视图（功能对比卡片）的信息比当前布局更直接、更重要，但缺少"做这件事多难"的维度。需要融合。

## Problem Statement

1. **「能做什么」分散**：基础能力在 Tab 1，DeFi 场景覆盖在 Tab 5
2. **「多难做」缺失**：effort_days、complexity rating 只在 Tab 5，决策者看 Tab 1 时完全看不到
3. **Tab 1 信息优先级错位**：签名方式细节（EIP-712 vs secp256k1）、置信度百分比对决策者决策价值低，却占据显眼位置

## Design: 「能力+成本」融合卡片

### 卡片新布局

```
┌─────────────────────────────────────────────┐
│  Privy          应用工具包           tee     │  ← 名称 + type + arch (不变)
├─────────────────────────────────────────────┤
│  ✅推荐 84%    Key: TEE+Shard    4链       │  ← 精简决策行 (verdict badge + custody + chain count)
├─────────────────────────────────────────────┤
│  基础能力                                    │
│  ✅创建钱包  ✅消息签名  ✅结构化签名        │  ← 不变
│  ✅转账交易  ✅多链支持  ✅预估手续费        │
├─────────────────────────────────────────────┤
│  DeFi 场景集成                     覆盖 4/4 │  ← 新增区块
│  🟡 Swap (1-2d)    🟡 借贷 (1-2d)          │
│  🟢 永续 (<1d)     🟡 预测 (2-3d)          │
│                                  DeFi 73.8  │
├─────────────────────────────────────────────┤
│  治理: [策略引擎] [限额] [白名单]           │  ← 不变
│▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔▔│
│ ████████████  Provider 色条                  │  ← 不变
└─────────────────────────────────────────────┘
```

### 信息变动明细

| 变动 | 内容 | 理由 |
|------|------|------|
| **新增** | 4 个 DeFi 场景 emoji + 难度标签 + effort days | 决策者最关心的「做什么+多难」 |
| **新增** | 覆盖率 (x/4) + DeFi 分 | 快速横向比较 |
| **精简** | pass rate 百分比环 → 缩为「推荐/谨慎/不推荐」badge + 百分比 | 降低视觉权重，释放空间 |
| **精简** | 支持链列表 → 改为数量显示 "N链" | 释放空间，详情页有完整列表 |
| **移除到详情页** | 签名方式详情（个人消息签名, EIP-712...） | 决策者不关心签名原语差异 |
| **移除到详情页** | 置信度百分比 | 技术指标，非决策信息 |
| **保留** | Key 托管模型 | 决策者关心安全 |
| **保留** | 治理标签（策略引擎/限额/白名单/HITL） | 决策者关心风控 |
| **保留** | Provider type + Architecture badge | 分类信息仍有价值 |

## Data Layer

**无需改 JSON 结构**。两个数据源已在 `loadData()` 的 `Promise.all` 中预加载：

- `currentData` ← `results/public_results.json`（provider 基础数据 + 测试结果）
- `decisionData` ← `web/data/decision_view.v1.json`（DeFi 场景成本数据）

在 `renderComparisonCards()` 中通过 `provider.id` 关联：

```javascript
const defiProvider = decisionData?.providers?.find(dp => dp.id === p.provider);
const defiScenarios = defiProvider?.defi?.scenarios || {};
const defiCoverage = defiProvider?.defi?.coverage || '0/0';
const defiScore = defiProvider?.defi?.scores?.equal || 0;
```

DeFi 场景字段结构（每个场景）：
```json
{
  "rating": "medium",          // simple | medium | complex | medium_complex | simple_conditional | not_feasible
  "label": "Medium",
  "emoji": "🟡",
  "effort_days": "1-2",       // "<1" | "1-2" | "2-3" | "2-4" | null (not feasible)
  "proxy": 0.65,
  "rationale": "...",          // 不在卡片显示，留给详情页
  "confidence": "high",
  "caveats": []
}
```

4 个场景 ID：`uniswap_swap`, `aave_morpho`, `hyperliquid`, `polymarket`

场景显示名映射：
- `uniswap_swap` → "Swap"
- `aave_morpho` → "借贷"
- `hyperliquid` → "永续"
- `polymarket` → "预测"

## Implementation Scope

- [ ] **AC-009-1**: 改造 `renderComparisonCards()` — 新增 DeFi 场景集成区块
- [ ] **AC-009-2**: 精简决策行（verdict badge + custody + chain count 替代 score ring + 完整链列表 + 签名方式）
- [ ] **AC-009-3**: 确认签名方式、置信度在详情页 `renderDetail()` 中仍可见
- [ ] **AC-009-4**: 新增 CSS 样式：`.comp-card-defi` 区块、verdict badge、DeFi 场景格子
- [ ] **AC-009-5**: 验证 `decisionData` 加载时序 — 确保 `renderComparisonCards` 被调用时 `decisionData` 已就绪
- [ ] **AC-009-6**: 笔记本屏幕宽度（1366px ~ 1440px）下 6 张卡片可读性验证
- [ ] **AC-009-7**: DeFi 数据缺失时的 graceful fallback（如 `decisionData` 加载失败，DeFi 区块显示「暂无数据」）

## Anti-Recommendations（不要做的事）

- ❌ **不要在卡片里塞 rationale 文本** — 每个场景的详细理由（如"eth_sendTransaction + data field via REST"）是技术细节，放详情页
- ❌ **不要删除决策视图 tab** — 它的权重选择器（equal/defi_heavy/trading_heavy）、排名对比、场景推荐卡片仍有独立价值
- ❌ **不要改 `public_results.json` 结构** — 它是 Python runner 的输出，改它需要改 runner.py
- ❌ **不要合并两个 tab 成超长页面** — 信息过载 + 滚动地狱
- ❌ **不要在 DeFi 区块用 tooltip 塞额外信息** — 移动端不支持 hover，保持可见信息自足

## 实施澄清项

1. **「N链」数据来源**：取 `provider_meta.chains` 数组，通过 `mapChainName()` 映射后去重（`[...new Set(chains.map(mapChainName))]`），取 `.length`
2. **DeFi 场景 emoji**：直接使用 `decision_view.v1.json` 中每个场景对象的 `emoji` 字段（如 `"🟡"`），不做二次映射
3. **签名方式 / 置信度 — 详情页已有**：`renderDetail()` 的「链与签名」卡片 (L1369-1374) 展示完整链列表 + 签名方式标签，无需改动
4. **V1 限制**：当前只支持固定 4 个场景（`uniswap_swap`, `aave_morpho`, `hyperliquid`, `polymarket`），扩展需修改前端 `SCENARIO_NAMES` 映射

## Effort Estimate

2-3 小时：
- `renderComparisonCards()` 改造: ~1.5h
- CSS 样式调整: ~0.5h
- 时序验证 + fallback + 宽度测试: ~0.5h
