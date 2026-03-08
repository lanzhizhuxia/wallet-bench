# ISSUE-026 — Dashboard v2：场景选择器 + FitScore 排序 + 覆盖度徽章

**Status**: OPEN  
**Priority**: P1  
**Created**: 2026-03-08  
**Depends on**: ISSUE-024（评分公式）, ISSUE-025（新测试数据）

---

## 背景

ISSUE-024 定义了双评分体系（FitScore + PlatformScore），ISSUE-025 补齐了测试项。本 ISSUE 将这些变化落地到 Dashboard UI。

---

## 一、核心 UI 变化

### 1. 雷达图改为 9 维

**现有 7 维**:
```
wallet_core, governance, reliability, ops, app, security, agent
```

**新 9 维**:
```
wallet_basics, agent_autonomy, performance, enterprise_readiness,
swap, defi_lending, cross_chain, prediction_market, perps
```

- 雷达图 9 个角，每个角 0-100
- 不支持的场景显示为 0（灰色），视觉上直接展示供应商的"形状"
- 维度标签使用中文简称

### 2. 场景选择器（默认首页）

在排行榜顶部新增场景选择器：

```
[全部] [Swap] [DeFi借贷] [跨链] [预测市场] [永续]
```

- 选择"全部"→ 按 PlatformScore 排序
- 选择某场景 → 按 FitScore_j 排序
- 不支持该场景的供应商灰色展示在底部，标注"不支持此场景"

### 3. 覆盖度徽章

每个供应商卡片上展示：

```
Coverage: ●●●○○ (3/5)
```

- 实心圆 = 该场景分 ≥ 40
- 空心圆 = 该场景分 < 40 或不支持

### 4. 功能对比卡片更新

- 移除旧的 7 维分数展示
- 改为：PlatformScore + 5 个场景独立分 + Agent 自主性分 + 性能分
- 企业就绪度折叠展示（默认收起）

### 5. 详情页更新

- 雷达图改为 9 维
- 测试结果表按新维度分组
- 新增"最佳场景"高亮提示

---

## 二、评分展示逻辑

### 排行卡片展示

```
┌─────────────────────────────┐
│ #1 Coinbase AgentKit   84.2 │  ← PlatformScore 或 FitScore
│ ●●○○○ Coverage 2/5         │
│                             │
│ Swap: 78  DeFi: --  跨链: --│  ← 场景分，-- 表示不支持
│ 预测: --  永续: --           │
│                             │
│ 🤖 Agent: 65  ⚡ 性能: 72  │
│ 🔑 基础: 88  🏢 企业: 54   │
└─────────────────────────────┘
```

### FitScore 模式展示

选择"Swap"场景后：

```
FitScore 排序：Swap 场景
┌─────────────────────────────┐
│ #1 Universal Trading   82.1 │  ← FitScore_swap
│ Swap: 90 → 权重 55%         │
│ Agent: 65 → 权重 20%        │
│ 性能: 72 → 权重 15%         │
│ 基础: 50 → 权重 10%         │
└─────────────────────────────┘
```

---

## 三、实现 Checklist

### Phase 1 — 雷达图 + 评分公式
- [ ] `RADAR_DIMENSIONS` 改为 9 维定义
- [ ] `TEST_CATEGORY` 映射表更新
- [ ] `computeRadarScores()` 重写
- [ ] 实现 `computeFitScore(provider, scenario)` 函数
- [ ] 实现 `computePlatformScore(provider)` 函数
- [ ] 实现 `computeCoverage(provider)` 函数

### Phase 2 — 场景选择器
- [ ] 新增场景选择器 UI 组件
- [ ] 选择场景后按 FitScore 重排序
- [ ] 不支持场景的供应商灰色下沉

### Phase 3 — 卡片 + 详情
- [ ] 功能对比卡片重新设计
- [ ] 覆盖度徽章组件
- [ ] 详情页 9 维雷达 + 新分组
- [ ] v1→v2 迁移说明（旧排名对比）

---

## 四、注意事项

- 雷达图 9 维时需要调整字体大小避免标签重叠
- FitScore 和 PlatformScore 需要在 URL hash 中持久化，方便分享链接
- 场景分为 0 的维度在雷达图上不要完全贴中心点，留最小半径避免视觉消失
- 保持 Binance Dark 设计风格不变
