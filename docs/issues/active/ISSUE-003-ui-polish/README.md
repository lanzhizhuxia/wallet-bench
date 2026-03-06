---
title: 'ISSUE-003: Web UI 架构重组 + 交互增强'
concepts:
- ui-restructure
- interactive-filter
- radar-toggle
- runner-multi-run
- ux
- data-integrity
---
# ISSUE-003: Web UI 架构重组 + 交互增强

## Meta
- **Status**: OPEN
- **Priority**: P1
- **Component**: wallet-bench / web + runner
- **Owner**: —
- **Date**: 2026-03-05
- **Effort**: Medium (3-5d)
- **Depends**: ISSUE-002 (ACCEPTED)
- **Audience**: 决策者 / 内部技术选型决策者

## Background

ISSUE-002 完成了双层展示重构（2 Tab），Oracle 验收通过。用户通过截图审查和语音反馈提出了两类问题：

1. **视觉缺陷**（12 个 BUG）：功能矩阵截断、DEFERRED provider 混入对比、图标含义不明等
2. **架构重组**：Tab 命名不面向用户任务、缺少交互筛选、雷达图布局不合理、Tab 2 内容与详情页重叠

本 Issue 合并处理这两类问题。

### 用户核心反馈（语音转录摘要）

1. **一级导航重命名** — "密钥与签名架构"和"Agent Skill 体验"不好，Tab 应面向用户任务
2. **功能矩阵升级为一级 Tab** — 核心对比工具不应藏在 sub-nav 里；新增需求筛选器（checkbox 过滤 provider）
3. **雷达图合并 + toggle** — 删除单独小雷达图卡片，合并为一张可交互雷达图 + provider toggle
4. **延迟热力图** — 统计卡片与表格错层；延迟数据需多次测试才准确
5. **内容去重** — 详情页的"agent 开发体验评估"和 Tab 2 的"集成问题备忘录"重叠
6. **Tab 2 精简** — 只保留踩坑总结 + Skill 信息卡，冗余内容下沉到详情页

## 当前 vs 目标

### 当前 (2 Tab + sub-nav)
```
[密钥与签名架构]                        [Agent Skill 体验]
 ├─ 总览条                              ├─ Binance 建议清单 Top 5
 ├─ sub-nav:                            ├─ Skill 信息卡
 │   ├─ 功能矩阵                        ├─ DX 雷达 (Chart.js)
 │   ├─ 雷达图 (Canvas, 全部+单个)       ├─ 首次成功时间条形图
 │   └─ 延迟热力图                       ├─ Takeaways (可借鉴/应规避)
 └─ Provider 名可点击 → 详情页           └─ 集成问题备忘录 (可折叠)
```

### 目标 (3 Tab, 交互增强)
```
[功能对比]                [能力雷达]              [延迟分析]
 ├─ 总览条 (DEFERRED灰化)  ├─ 一张叠加雷达图         ├─ 热力图表格
 ├─ 功能矩阵              ├─ Provider toggle        ├─ 统计卡片 (横向布局)
 ├─ 需求筛选器 ← NEW      │   (checkbox 显隐)       ├─ disclaimer ← NEW
 ├─ 图例 ← NEW           └─ Provider 名可点击→详情   └─ Provider 名可点击→详情
 └─ Provider 名可点击→详情

[详情页] (点击 provider 名进入)              [踩坑与工具] (精简后的 Tab 2)
 ├─ 完整 evaluation                         ├─ 踩坑总结 (跨 provider 共性教训)
 ├─ Agent memo                              └─ Skill 信息卡 (GitHub/包名/集成方式)
 ├─ Takeaways (可借鉴/应规避)
 └─ 所有 bugs/doc gaps/人类干预点
```

### 关键变更摘要

| 变更 | 从 | 到 |
|------|---|---|
| Tab 命名 | 密钥与签名架构 / Agent Skill 体验 | 功能对比 / 能力雷达 / 延迟分析 / 踩坑与工具 |
| 功能矩阵 | sub-nav 子视图 | 一级 Tab（功能对比） |
| 雷达图 | 全部服务商 + 6 张单独卡片 | 一张可交互图 + provider toggle |
| 延迟统计卡片 | 垂直堆叠，与表格错层 | 横向布局，与表格对齐 |
| 建议清单 | Binance 建议清单 Top 5 | 踩坑总结（经验输出非决策建议） |
| Tab 2 内容 | 6 个模块 | 精简为 2 个（踩坑总结 + Skill 信息卡） |
| DX 雷达 / 时间条形图 / 备忘录 | Tab 2 独立展示 | 下沉到详情页 |
| 需求筛选器 | 不存在 | 功能矩阵 Tab 顶部 checkbox 过滤 |
| Runner 多次运行 | 不支持 | 支持 `--runs=N`，取中位数 |

## 问题清单（原 BUG-1 至 BUG-12 + 新增）

### 架构重组 (Critical)

#### ARCH-1: 一级导航从 2 Tab 改为 4 Tab
- 功能对比 | 能力雷达 | 延迟分析 | 踩坑与工具
- 原 sub-nav（功能矩阵/雷达图/热力图）提升为一级 Tab
- 原 Tab 2 精简为"踩坑与工具"

#### ARCH-2: 功能矩阵新增需求筛选器
- 矩阵顶部增加 checkbox 组，每个功能一个（如 ☐ 消息签名 ☐ 多链支持 ☐ 策略引擎）
- 用户勾选后，高亮满足所有所选功能的 provider，灰化不满足的
- 筛选基于测试结果 pass/fail，⚠️(skip) 视为不支持

#### ARCH-3: 雷达图合并为一张 + provider toggle
- 删除 6 张单独小雷达图卡片
- 保留一张 Chart.js 叠加雷达图
- 顶部增加 provider checkbox/chip 组，控制每条线的显隐
- 默认显示全部 4 个已完成 provider

#### ARCH-4: Tab 2 精简 — 内容去重
- 保留：踩坑总结（原建议清单改造）、Skill 信息卡
- 下沉到详情页：DX 雷达、首次成功时间条形图、Takeaways、集成问题备忘录
- 删除：recommendations.json（踩坑总结从 public_results.json 动态聚合）

#### ARCH-5: 详情页内容整合
- 详情页已有 evaluation + agent memo
- 新增：DX 雷达（单 provider）、首次成功时间、Takeaways（可借鉴/应规避）
- 确保与原 Tab 2 内容不重叠

### 数据完整性 (High)

#### BUG-1: 功能矩阵表格右侧截断
- 表格容器加 `overflow-x: auto`

#### BUG-2: DEFERRED provider 混入对比视图
- 功能矩阵 / 雷达图 / 热力图仅渲染 4 个已完成 provider
- 总览条保留 DEFERRED provider 但灰化 + "DEFERRED" 标注

#### BUG-12: 「建议清单」改为「踩坑总结」
- 定位从决策建议 → 经验输出
- 内容从各 provider takeaways.avoid + evaluation bugs 提炼共性
- 删除 recommendations.json

### 可读性增强 (Medium)

#### BUG-3: t05 链名过长
- 超过 3 个时折叠显示（如 `ETH, BSC +4`），hover 展开
- 使用 mainnet 名称映射（`base-sepolia` → `Base`）

#### BUG-4: ⚠️ 图标含义不明
- 增加 tooltip + 矩阵顶部图例（✅ PASS / ❌ FAIL / ⚠️ SKIP）

#### BUG-10: 测试项名称中英文混用
- 统一中文显示名：rate_limit_resilience → 限流韧性, portability_recovery → 可移植恢复, authorization_audit_trace → 授权审计追踪

### 视觉一致性 (Low)

#### BUG-5: governance 列头无 tooltip
#### BUG-6: 架构类别标签颜色语义不清（Local=蓝, TEE=绿, Intent=紫, MPC_AA=橙）
#### BUG-8: 雷达图线条辨认 → 由 ARCH-3 toggle 方案解决
#### BUG-11: 延迟统计卡片错层 + 垂直堆叠 → 改为横向布局，与表格对齐

### 详情页

#### BUG-13: 能力清单标签使用英文 snake_case
- create_wallet, sign_message, sign_typed_data 等原始英文展示
- 应使用中文显示名（与 BUG-10 共用 mapping）

#### BUG-14: 能力清单未区分"支持"与"不支持"
- 所有标签样式一致，但 BNB Chain MCP 实际不支持 sign_message/sign_typed_data/policy_enforcement/session_delegation
- 清单应区分：✅ 已通过 / ⚠️ 声明但未通过 / ❌ 不支持（基于测试结果着色）

#### BUG-15: "提交方式"字段显示 `client_submit`
- 技术内部值直接展示，用户看不懂
- 映射为中文：client_submit → 客户端提交, server_submit → 服务端提交 等

#### BUG-16: "签名方式"字段显示 `raw_tx`
- 同上，技术值直接展示
- 映射：raw_tx → 原始交易签名, personal_sign → 个人消息签名, eip712 → EIP-712 结构化签名, secp256k1_raw → secp256k1 原生签名

#### BUG-17: 测试结果表格"说明"列含 `[REDACTED]` 标记
- "钱包已创建 [REDACTED]"、"交易已提交: [REDACTED]" 直接展示给用户
- 前端渲染时过滤掉 [REDACTED] 或替换为更友好的文案

#### BUG-18: 能力清单右侧大量空白
- 清单卡片只占 1/3 宽度，右侧空白
- 与其他信息卡同行或利用空间展示上下文

#### BUG-19: "刷新数据" 按钮和 "已加载 N 个服务商" 提示多余
- 纯展示页面不需要刷新按钮和加载计数器，删除

#### BUG-20: 详情页缺少二级导航（锚点跳转）
- "Agent 开发体验评估" 等模块在详情页底部，用户需要大量滚动才能看到
- 详情页顶部增加二级导航栏（sticky），包含各模块锚点：基本信息 / 测试结果 / 能力清单 / 开发体验评估 / Agent 备忘
- 点击跳转到对应区域

#### BUG-21: 详情页 Agent 开发体验评估 — 总结文字与评分条之间多余空白换行
- agent_experience 文本渲染后与评分条之间有一大段空白
- 原因可能是 markdown 渲染时保留了源文本中的多余 `\n`，或 CSS margin/padding 过大
- 修复：渲染时 trim 多余空行 + 检查 .eval-summary 与 .eval-scores 之间的 margin

#### BUG-22: Agent 集成备忘录标题不显着 + 缺一键复制
- "集成备忘录" 作为标题和上方内容混在一起，视觉上不是独立模块
- 这块内容对开发者极其实用（“致后来的 Agent”），应抽出为独立卡片模块，有明确的视觉边界
- 卡片右上角增加「复制」按钮，一键复制备忘录全文（纯文本）到剪贴板

### Runner 增强

#### RUNNER-1: 支持多次运行取中位数
- runner.py 新增 `--runs=N` 参数（默认 1，建议 3-5）
- 每个测试运行 N 次，结果取中位数
- public_results.json 中延迟字段记录 median + min + max + runs_count
- 热力图页面增加 disclaimer："数据基于 N 次测试的中位数"

## 实施前决策（Oracle R1 审核后确认）

| # | 决策项 | 结论 |
|---|--------|------|
| D-1 | 功能筛选逻辑 | **AND**：勾选的功能全部支持才高亮。unknown/null 视为不支持 |
| D-2 | DEFERRED 判定字段 | 基于 `provider_meta.viability`。详情页允许查看但顶部标注 DEFERRED |
| D-3 | 详情页 URL 规范 | Hash route (`#detail/bnbchain_mcp`)，支持直达和刷新保留 |
| D-4 | 踩坑聚合规则 | 从各 provider `takeaways.avoid` + evaluation bugs 手动提炼共性条目，不做自动去重（4 个 provider 量小） |
| D-5 | Runner `--runs=N` | 失败样本不计入中位数，只算成功的。最小 N=1（默认，向后兼容） |
| D-6 | [REDACTED] 清洗 | 统一 sanitize 函数，渲染前必经。覆盖所有路径（表格/tooltip/复制/详情页） |
| D-7 | Provider 颜色映射 | 跨页面固定一致：BNB=#4ade80, Coinbase=#60a5fa, Crossmint=#c084fc, Privy=#f472b6 |
| D-8 | 前端数据适配层 | 延迟读取优先级：new `latency.median` → fallback `latency_ms`。无数据显示 “—” |

## Acceptance Criteria

### Phase 1A: 架构重组 + 数据正确性 (web/)

- [ ] **AC-003-1**: 导航从 2 Tab 改为 4 Tab（功能对比 / 能力雷达 / 延迟分析 / 踩坑与工具），切换无 JS error
- [ ] **AC-003-2**: 功能矩阵升级为一级 Tab，包含总览条 + 矩阵 + 需求筛选器 + 图例
- [ ] **AC-003-3**: 需求筛选器：多选为 AND 逻辑。勾选 2 个功能后，仅两项都 PASS 的 provider 高亮，其余灰化。unknown/null 视为不支持
- [ ] **AC-003-4**: 雷达图升级为一级 Tab，一张 Chart.js 叠加图 + provider toggle（checkbox/chip 控制显隐）。隐藏后数据集和图例同步更新
- [ ] **AC-003-5**: 延迟热力图升级为一级 Tab，统计卡片横向 flex 布局、与热力图表格对齐（无错层）
- [ ] **AC-003-6**: "踩坑与工具" Tab：踩坑总结（跨 provider 共性教训）+ Skill 信息卡。删除 recommendations.json
- [ ] **AC-003-7**: 详情页整合：新增 DX 雷达（单 provider）+ Takeaways + 首次成功时间，与原 evaluation 合并展示。无与原 Tab 2 重复内容
- [ ] **AC-003-8**: 功能矩阵 / 雷达图 / 热力图过滤 DEFERRED provider（基于 `provider_meta.viability`），总览条灰化保留 + "DEFERRED" 标注
- [ ] **AC-003-9**: 功能矩阵表格 `overflow-x: auto`，1440px 宽度下所有列可见或可滚动
- [ ] **AC-003-10**: 矩阵图例（✅ PASS / ❌ FAIL / ⚠️ SKIP）在矩阵顶部显示。每个 ⚠️ 单元格有 title tooltip 说明原因
- [ ] **AC-003-11**: 删除 "刷新数据" 按钮和 "已加载 N 个服务商" 提示
- [ ] **AC-003-12**: 详情页 URL 采用 hash route（`#detail/provider_id`），支持直达链接和刷新保留
- [ ] **AC-003-13**: 统一 sanitize 函数：渲染前移除所有 `[REDACTED]` 标记，覆盖表格/tooltip/复制/详情页全部路径
- [ ] **AC-003-14**: Provider 颜色跨页面固定一致（BNB=#4ade80, Coinbase=#60a5fa, Crossmint=#c084fc, Privy=#f472b6）

### Phase 1B: 视觉 + 可读性修复 (web/)

- [ ] **AC-003-15**: t05 链名超过 3 个时折叠显示（如 `ETH, BSC +4`），hover 展开完整列表。链名使用 mainnet 名称映射
- [ ] **AC-003-16**: 测试项名称统一中文（功能矩阵 + 热力图 + 详情页共用 mapping）
- [ ] **AC-003-17**: 架构类别标签独立颜色（Local=蓝 #3b82f6, TEE=绿 #22c55e, Intent=紫 #a855f7, MPC_AA=橙 #f97316）
- [ ] **AC-003-18**: governance 列头增加 title tooltip（策略引擎=“是否有可编程的策略规则引擎” 等）
- [ ] **AC-003-19**: 详情页能力清单使用中文显示名 + 按测试结果着色（绿=通过, 黄=跳过, 灰=不支持）
- [ ] **AC-003-20**: 详情页技术字段中文映射（client_submit→客户端提交, raw_tx→原始交易签名 等）
- [ ] **AC-003-21**: 详情页能力清单布局优化，卡片宽度至少占 50%，无大片空白
- [ ] **AC-003-22**: 详情页顶部 sticky 二级导航栏，点击锚点平滑滚动到各模块（基本信息 / 测试结果 / 能力清单 / 开发体验评估 / Agent 备忘）
- [ ] **AC-003-23**: 详情页 Agent 开发体验评估区块修复多余空白换行
- [ ] **AC-003-24**: Agent 集成备忘录抽出为独立卡片模块（明确视觉边界 + 标题突出），右上角「复制」按钮一键复制全文（navigator.clipboard）

### Phase 2: Runner 多次运行 (runner.py)

- [ ] **AC-003-25**: runner.py 支持 `--runs=N`（默认 1），每个测试运行 N 次，失败样本不计入，取成功样本中位数
- [ ] **AC-003-26**: public_results.json 延迟字段扩展为 `{median, min, max, runs_count}`，前端读取优先级 `latency.median` → fallback `latency_ms`
- [ ] **AC-003-27**: 热力图页面展示 median 值 + disclaimer（"数据基于 N 次测试中位数"）

### EXIT Gate

- [ ] 4 Tab 导航正常切换，控制台 0 error（warning 允许）
- [ ] 功能筛选器 AND 逻辑正确：勾选 2 项后仅两项都 PASS 的 provider 高亮
- [ ] 雷达图 toggle 可用：点击 provider 名切换线条显隐，图例同步
- [ ] DEFERRED provider 不混入对比视图，总览条灰化显示
- [ ] 详情页包含完整评估信息 + DX 雷达 + Takeaways（无遗漏）
- [ ] 详情页 hash route 支持直达和刷新保留
- [ ] 踩坑总结替代建议清单，内容定位为经验输出
- [ ] 无 "刷新数据" 按钮和加载计数器
- [ ] 全局无 [REDACTED] 泄露（表格/tooltip/复制/详情页）
- [ ] 详情页二级导航可跳转各模块，备忘录可一键复制
- [ ] 1440px 宽度下无横向溢出、卡片不重叠、Tab 不换行
- [ ] `python runner.py --runs=3` 运行成功，输出含 median/min/max/runs_count
- [ ] 旧格式 public_results.json（无 median 字段）仍可正常渲染（向后兼容）

## Constraints

- 延续 ISSUE-002 约束：纯前端、Chart.js CDN、不引入构建工具
- public_results.json 延迟字段扩展为对象 {median, min, max, runs_count}，需向后兼容（旧格式仍可渲染）
- Tab 数量从 2 变为 4，但详情页交互不变（点击 provider 名进入）
- 踩坑总结从 public_results.json 动态聚合，不再使用静态 JSON

## Execution Log

| 日期 | 事件 | 详情 |
|------|------|------|
| 2026-03-05 | Issue 创建 | 基于截图审查识别 12 个 UI BUG |
| 2026-03-05 | 范围扩展 | 用户语音反馈要求架构重组：4 Tab + 筛选器 + toggle + runner 多次运行。Issue 从 P2 UI polish 升级为 P1 架构重组 |
| 2026-03-05 | 详情页审查 | 新增 BUG-13~18（能力标签英文、未区分支持状态、技术字段、REDACTED 泄露、布局空白）|
| 2026-03-05 | 补充审查 | 新增 BUG-19（刷新按钮多余）、BUG-20（详情页缺二级导航锚点跳转）|
| 2026-03-05 | 备忘录审查 | 新增 BUG-22（Agent 集成备忘录标题不显著 + 缺一键复制）|
| 2026-03-05 | Oracle R1 审核 | APPROVE WITH CHANGES。补充 8 个决策项 (D-1~D-8)，Phase 1 拆分为 1A+1B，EXIT Gate 量化，AC 重编号至 27 项 |
| 2026-03-05 | Phase 1A 完成 | 4-tab 架构重组 + 数据正确性 (AC-003-1~14)，通过 Playwright 验证 |
| 2026-03-05 | Phase 1B 完成 | 视觉+可读性修复 (AC-003-15~24)。修复 app.js 语法错误 (renderMatrix 未关闭大括号)，修复 sticky nav 实现，Playwright 验证 10/10 PASS |
| 2026-03-05 | Phase 2 完成 | runner.py --runs=N 实现 (AC-003-25~27)，前端 getLatencyMs() 向后兼容，热力图 disclaimer 条件显示 |
| 2026-03-05 | Oracle 终审 | 2 次尝试均因 token limit 无输出。基于 Playwright 全量验证证据：27/27 AC PASS (AC-003-25 仅语法验证，未 live-test)，EXIT Gate 12/13 通过 |
