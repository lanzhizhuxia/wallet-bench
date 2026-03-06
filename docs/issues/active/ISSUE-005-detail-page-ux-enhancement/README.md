---
title: 'ISSUE-005: 详情页 UX 增强'
concepts:
- detail-page
- ux-enhancement
- information-hierarchy
- binance-theme-consistency
---
# ISSUE-005: 详情页 UX 增强

## Meta
- **Status**: OPEN
- **Priority**: P1
- **Component**: wallet-bench / web (app.js + style.css)
- **Owner**: —
- **Date**: 2026-03-05
- **Effort**: Medium (1-2d)
- **Depends**: ISSUE-004（Binance 主题迁移完成后实施）
- **Source**: Oracle UI/UX Review R3 (session `ses_34251b77effe`)
- **Audience**: 决策者 / 外部演示

## Background

ISSUE-004 完成了 Binance Dark Midnight 主题迁移，视觉层面已对齐。但详情页（`#detail/{provider}`）的 **信息架构和交互体验** 仍有明显短板：用户进入后无法一眼看出结论，测试表无筛选、memo 过长、score bar 色彩语义混乱、sub-nav 与主 Tab 风格不一致。

Oracle R3 审查后给出 10 条排序建议，本 Issue 将其拆解为可验收的 AC。

## 核心目标

1. **决策优先** — 用户进入详情页 3 秒内能看到结论（好/一般/差 + 关键数字）
2. **扫描效率** — 测试结果按严重性排序 + 可筛选，失败项一目了然
3. **信息密度** — 长内容可折叠，重要信息前置
4. **Binance 语义一致** — score bar、nav 等组件颜色统一到 Binance 语义体系

## Phase 1: 信息层级重构 (High Impact)

### AC-005-1: 结论条（Decision Bar）
在 H2 "服务商详情" 下方、sub-nav 上方，新增一行紧凑的结论摘要：
- 总体评价标签（推荐 / 谨慎 / 不推荐，基于 pass 率阈值）
- Pass 率百分比（如 "12/16 通过 75%"）
- 中位延迟（如 "p50: 320ms"）
- Top blocker（如 "❌ 会话委托不可用"）— 取第一个 fail/error 的 `TEST_NAME_ZH` 映射名
- 评价标签颜色：推荐=`--color-pass`，谨慎=`--color-skip`，不推荐=`--color-fail`
- 阈值：≥80% pass → 推荐，50-79% → 谨慎，<50% → 不推荐
- **空数据兜底**：`results` 为空/undefined 时显示 "暂无测试数据"，评价标签不渲染；p50 无延迟数据时显示 "—"；无 fail/error 时 blocker 区域不渲染
- **Mobile (375px)**：结论条 flex-wrap，标签和数字各自占一行

### AC-005-2: Score Bar 语义化配色
将 `renderScoreBar()` 的 HSL hue 渐变替换为 Binance 语义色：
- 1-2/5 分 → `--color-pass`（绿，分数越低=摩擦越小=越好）
- 3/5 分 → `--color-skip`（黄，中等）
- 4-5/5 分 → `--color-fail`（红，摩擦大=差）
- 注：DX 评分体系中 1=best 5=worst，颜色需反映"对用户的影响"

### AC-005-3: 单 Provider 雷达图替换为分数条
详情页 Card 3（开发体验雷达）从 Chart.js radar 改为 **5 维度水平分数条 + 总分**：
- 5 个维度（复用 `computeRadarScores()` 返回值）：capability（能力广度）、reliability（可靠性）、dx_quality（开发体验）、latency_score（延迟）、coverage（覆盖度）
- 总分 = 5 维度算术平均，取整
- 每个维度显示中文标签 + 百分比数值 + 水平进度条
- 总分突出显示（字号 1.4rem + 语义色标签）
- 颜色用语义色（≥80 `--color-pass`、60-79 `--color-skip`、<60 `--color-fail`）
- Card 标题改为 "综合评分"
- 不再调用 `renderDetailDxRadar()`，不再创建 `<canvas>` 元素

## Phase 2: 测试结果表增强 (High Impact)

### AC-005-4: 测试结果表 Mini-Filter
在测试结果表上方添加一行按钮组筛选器：
- 按钮：全部 | 失败 (N) | 跳过 (N) | 通过 (N)
- 括号中显示各状态的数量；**数量为 0 时按钮仍显示但 disabled + opacity 0.4**
- 默认选中"全部"
- 点击筛选后，表格只显示对应状态的行（JS `display:none` 切换，不重建 DOM）
- 按钮样式：pill 形状，选中态使用对应语义色（通过=绿底、失败=红底、跳过=黄底、全部=`--bg-elevated`）
- **Mobile (375px)**：按钮组 flex-wrap，每行放 2 个

### AC-005-5: 测试结果默认排序
测试结果表默认排序改为：
1. 失败 (fail) 优先
2. 错误 (error) 次之
3. 跳过 (skip) 次之
4. 通过 (pass) 最后
5. 同状态内按延迟降序

### AC-005-6: 失败项摘要
在测试结果表上方（filter 下方）、当存在 fail/error 结果时，显示一行红色摘要：
- "⚠️ N 项失败：{test_name_1}、{test_name_2}..."
- 使用 `--color-fail` 文字色
- 不存在 fail/error 时不显示

## Phase 3: 内容折叠与信息密度 (Medium Impact)

### AC-005-7: Memo 卡片默认折叠
Agent 集成备忘录默认只显示前 6 行内容：
- 超出部分隐藏（`max-height` + `overflow:hidden`），底部显示渐变遮罩 + "展开全文 ▼" 按钮
- 点击展开后按钮变为 "收起 ▲"
- Copy 按钮始终可见，复制完整内容（不受折叠影响）
- 边框从 2px yellow 降为 1px `--bg-border` + header 区域黄色强调
- **Memo 内容 ≤6 行时**：不显示折叠按钮和渐变遮罩，直接全部展示

### AC-005-8: 能力清单 Tag Tooltip
为每个 capability tag 添加 tooltip（hover 显示）：
- 内容来源：优先查找 `TEST_DESCRIPTIONS[CAP_TO_TEST[cap]]`，fallback 到 `CAP_NAME_ZH[cap]`
- 使用 `title` 属性即可（无需自定义 tooltip 组件）
- 格式："创建钱包 — 验证能否通过 API 生成新密钥对并返回有效地址"
- 无映射的 capability 显示 key 原文作为 tooltip

## Phase 4: 视觉微调 (Low Impact)

### AC-005-9: H2 与 Sub-Nav 边界去重
- 移除 H2 "服务商详情" 的 `border-bottom`（避免与 sub-nav 底线双线）
- Sub-nav sticky 状态时添加 `box-shadow: 0 1px 4px rgba(0,0,0,0.5)` 分层感

### AC-005-10: Sub-Nav 颜色对齐主 Tab
- 默认色从 `--text-secondary` 改为 `--text-tertiary`（与主 Tab `.tab` 一致）
- Hover 保持 `--text-primary`
- Active 保持 `--brand-yellow`

### AC-005-11: Card Grid 布局优化
重排详情页 card grid 顺序，信息优先级更合理：
1. Row 1 (full-width): 综合评分（原 DX 雷达 → AC-005-3 改造后的分数条）
2. Row 2 (2-col): 关键要点 + 架构信息
3. Row 3 (2-col): 链与签名 + （空位，不渲染占位卡片，CSS grid 自动补位）
4. Row 4 (full-width): 能力清单

### AC-005-12: Deferred Banner 条件渲染
将 `#detail-provider-banner` 从 HTML 固定元素 + `display:none` 改为 JS 条件插入：
- 仅当 `DEFERRED_PROVIDERS.includes(provider.provider)` 时才创建 banner DOM
- 非 deferred 时不渲染任何 banner 节点

## EXIT Gate

- [ ] 详情页顶部有结论条，3 秒内可判断 provider 质量
- [ ] Score bar 使用语义色（绿/黄/红），不再有 HSL 彩虹渐变
- [ ] 测试结果表有筛选按钮 + 失败优先排序
- [ ] Memo 默认折叠，展开/收起正常
- [ ] Sub-nav 与主 Tab 颜色体系一致
- [ ] 0 JS error，所有 6 个 provider 详情页正常渲染
- [ ] 375px / 768px / 1440px 无溢出

## Execution Log

| 日期 | 事件 | 详情 |
|------|------|------|
| 2026-03-05 | Oracle 审查 | Oracle R3 对详情页 UI/UX 提出 10 条改进建议 |
| 2026-03-05 | Issue 创建 | 4 Phase + 12 AC + EXIT Gate |
| 2026-03-05 | Oracle R1 审核 | APPROVE WITH CHANGES — 6 条反馈已合入（空数据兜底、filter 0 计数、mobile 换行、memo ≤6行、tooltip 来源、grid 空位） |
| 2026-03-05 | 实现完成 | 12/12 AC 全部实现。Playwright 验证 18/18 通过（6 providers × 3 viewports: 1440/768/375px），0 JS error，0 overflow |
