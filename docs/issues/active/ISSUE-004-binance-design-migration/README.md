---
title: 'ISSUE-004: Binance 设计风格迁移'
concepts:
- design-system
- binance-style
- css-migration
- visual-identity
- dark-midnight-theme
---
# ISSUE-004: Binance 设计风格迁移

## Meta
- **Status**: OPEN
- **Priority**: P1
- **Component**: wallet-bench / web (style.css + index.html + app.js)
- **Owner**: —
- **Date**: 2026-03-05
- **Effort**: Medium (2-3d)
- **Depends**: ISSUE-003（架构重组完成后实施）
- **Spec**: `docs/DESIGN-SPEC.md`
- **Audience**: 决策者 / 外部演示

## Background

wallet-bench 当前使用 GitHub Dark 风格（蓝灰底 `#0d1117`、蓝色强调 `#58a6ff`、系统默认字体），视觉上与 Binance 品牌无关联。作为 Binance 内部钱包 benchmark 工具，需要对齐 Binance 官网设计语言，提升专业感和品牌归属。

设计规范已完成：`docs/DESIGN-SPEC.md`（基于 binance.com Dark Midnight 主题实地抓取的 CSS 变量、字体、组件规格）。

### 核心迁移目标

| 维度 | 现状 (GitHub Dark) | 目标 (Binance Midnight) |
|------|-------------------|----------------------|
| 页面底色 | `#0d1117`（蓝灰调） | `#000000`（纯黑） |
| 卡片底色 | `#161b22` | `#1A1A1A` |
| 边框色 | `#30363d` | `#3D3D3D` |
| 强调色 | `#58a6ff`（蓝色） | `#F0B90B`（Binance 黄） |
| CTA 按钮 | 灰底+白字 | `#FCD535` 黄底+黑字 |
| 通过色 | `#3fb950` | `#28A473` |
| 失败色 | `#f85149` | `#F63C55` |
| 字体 | system-ui 系统默认 | DM Sans + Noto Sans SC |
| Badge | 实色底+黑字 | 透明底+同色文字 |
| 表格密度 | 宽松 | 紧凑 (12px 16px) |
| 圆角 | 8px 统一 | 分级 (4-16px) |

## 实施方案

### Phase 1: CSS 变量体系重建
将 `style.css` 中 `:root` 下所有硬编码色值替换为 DESIGN-SPEC 定义的语义化 CSS 变量。

**变量分组**：
- 背景 7 级（`--bg-base` 至 `--bg-muted`）
- 文字 6 级（`--text-primary` 至 `--text-emphasis`）
- 品牌色 4 个（`--brand-yellow` 系列）
- 语义色 12 个（pass/fail/skip 各含 base + hover + bg + alpha）
- 间距 9 级（`--space-2xs` 至 `--space-4xl`）
- 圆角 7 级（`--radius-xs` 至 `--radius-circle`）
- Provider 专属色 6 个

### Phase 2: 字体引入
- HTML `<head>` 添加 Google Fonts link（DM Sans 400/500/600/700 + Noto Sans SC 400/500/700）
- CSS 中替换 `font-family` 为 `--font-display` / `--font-body` / `--font-mono`
- 校准字号体系（Display 36px → Caption 12px 共 7 级）

### Phase 3: 组件逐一迁移

#### 3a: 基础元素
- `body` 背景 → `--bg-base`
- 所有 `border-color` → `--bg-border`
- 所有硬编码文字色 → 对应 `--text-*` 变量
- `h2` 分割线 → `--bg-border`

#### 3b: 选项卡 (Tabs)
- 主 Tab 选中色 → `--brand-yellow`（含下划线）
- 子 Tab 选中态 → `--brand-yellow-alpha-10` 底 + `--brand-yellow` 文字
- hover → `--text-primary`

#### 3c: 表格
- 表头 → `--bg-card` 底、`--text-tertiary` 文字、12px、weight 400
- 表体 → 14px、`--text-primary`
- 行分割 → `--bg-border`
- hover 行 → `--bg-card`
- 单元格 padding → `12px 16px`
- Provider 列头 hover → `--brand-yellow`
- Pass/Fail/Skip 色 → 对应 `--color-pass/fail/skip`

#### 3d: 卡片
- 背景 → `--bg-card`
- 边框 → `--bg-border`
- 圆角 → `--radius-l` (12px)
- hover 边框 → `--bg-muted`

#### 3e: Badge（架构类别）
- 从实色底+黑字 → 透明底+同色文字（Binance 风格）
- Local → 绿色透明底
- TEE → 蓝色透明底
- Intent → 黄色透明底
- MPC+AA → 紫色透明底

#### 3f: 按钮
- Primary CTA → `--brand-yellow-btn` (#FCD535) 底 + `--text-on-yellow` (#000) 字
- Ghost → transparent + `--bg-border` 边框
- Link → `--brand-yellow`

#### 3g: 雷达图 / 热力图 / 柱状图
- 网格线 / 轴标签 → `--bg-border` / `--text-tertiary`
- 热力图色阶 → 对齐 Binance 绿-黄-红
- 柱状图柱体 → `--brand-yellow`

#### 3h: 评估区 / 折叠面板 / 备忘录
- 评估区强调线 → `--brand-yellow`（原为蓝色）
- 折叠面板 → `--bg-card` + `--bg-border`
- 备忘录代码块 → `--font-mono`

### Phase 4: 布局微调
- `max-width` → `1248px`（Binance 标准）
- 间距替换为 `--space-*` 变量
- 响应式断点对齐（768px / 1081px）

### Phase 5: 视觉验收
- 截图对比 Binance Markets 页面
- 检查所有组件在 1440px / 1080px / 768px 下的表现
- 确认无硬编码色值残留

## Acceptance Criteria

### Phase 1: CSS 变量 (style.css)

- [ ] **AC-004-1**: `:root` 中定义全部语义化 CSS 变量（背景 7 级 + 文字 6 级 + 品牌 4 个 + 语义 12 个 + 间距 9 级 + 圆角 7 级 + Provider 6 个），共 ≥51 个变量
- [ ] **AC-004-2**: `style.css` 中无硬编码色值（`#` 开头的颜色声明仅出现在 `:root` 变量定义中）
- [ ] **AC-004-3**: 页面底色为 `#000000`（纯黑），卡片底色 `#1A1A1A`，边框 `#3D3D3D`

### Phase 2: 字体

- [ ] **AC-004-4**: Google Fonts 引入 DM Sans (400/500/600/700) + Noto Sans SC (400/500/700)，`<link>` 标签位于 `<head>` 中 CSS 之前
- [ ] **AC-004-5**: `body` font-family 替换为 `var(--font-body)`，等宽场景使用 `var(--font-mono)`
- [ ] **AC-004-6**: 字号体系完整实现（Display 36px / H1 24px / H2 18px / H3 15px / Body 14px / Caption 12px / Mono 13px）

### Phase 3: 组件迁移

- [ ] **AC-004-7**: 主 Tab 选中态为 `--brand-yellow` 文字 + 2px 黄色下划线
- [ ] **AC-004-8**: 子 Tab 选中态为 `--brand-yellow-alpha-10` 背景 + `--brand-yellow` 文字
- [ ] **AC-004-9**: 表头 12px / `--text-tertiary` / weight 400；表体 14px / `--text-primary`；单元格 `12px 16px`
- [ ] **AC-004-10**: 架构类别 Badge 改为透明底+同色文字（Local=绿, TEE=蓝, Intent=黄, MPC_AA=紫）
- [ ] **AC-004-11**: Primary CTA 按钮 `#FCD535` 黄底 + `#000` 黑字
- [ ] **AC-004-12**: 雷达图网格线 `--bg-border`，轴标签 `--text-tertiary`
- [ ] **AC-004-13**: 热力图色阶对齐 Binance 绿-黄-红（`hsl(160,60%,35%)` → `hsl(45,80%,45%)` → `hsl(0,70%,45%)`）
- [ ] **AC-004-14**: 柱状图柱体颜色 `--brand-yellow`
- [ ] **AC-004-15**: 评估区强调线/标题色 → `--brand-yellow`
- [ ] **AC-004-16**: Provider 雷达图颜色跨页面固定一致（见 DESIGN-SPEC §7 Provider 调色板）

### Phase 4: 布局

- [ ] **AC-004-17**: `max-width: 1248px`，移动端 padding 16px / 桌面端 24px
- [ ] **AC-004-18**: 所有间距使用 `--space-*` 变量，无硬编码 `rem` / `px` 间距值

### Phase 5: 验收

- [ ] **AC-004-19**: 1440px 宽度下截图与 Binance Markets 深色主题视觉风格一致（纯黑底、黄色强调、紧凑表格）
- [ ] **AC-004-20**: 768px 宽度下无布局溢出、Tab 不换行、卡片单列堆叠
- [ ] **AC-004-21**: 控制台 0 JS error，所有组件正常渲染
- [ ] **AC-004-22**: app.js 中无硬编码色值（所有内联颜色改用 CSS 变量或从 `getComputedStyle` 获取）

### EXIT Gate

- [ ] `style.css` 中 `:root` 外零硬编码色值
- [ ] 页面在 Chrome DevTools 中切换 375px / 768px / 1440px 三个宽度均无溢出
- [ ] 截图与 Binance Dark Midnight 主题视觉对齐（纯黑底、品牌黄强调、透明 badge、紧凑表格）
- [ ] 全部 22 个 AC 勾选完成

## Constraints

- **不动数据层**：本 Issue 仅改 CSS + 少量 HTML/JS 中的样式引用，不改数据结构
- **依赖 ISSUE-003**：在 ISSUE-003 架构重组完成后实施，避免两边同时改同一文件冲突
- **不引入构建工具**：延续纯前端约束（CSS 变量 + Google Fonts CDN + Chart.js CDN）
- **不使用 BinanceNova 字体**：私有字体，用 DM Sans 替代
- **向后兼容**：如果 public_results.json 使用旧格式，页面仍能正常渲染

## 文件影响范围

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `web/style.css` | **重写** | CSS 变量体系 + 所有组件样式迁移 |
| `web/index.html` | **小改** | 添加 Google Fonts link；可能调整少量 class 名 |
| `web/app.js` | **小改** | 内联样式中的硬编码色值替换为 CSS 变量引用 |
| `docs/DESIGN-SPEC.md` | **参考** | 不改动，作为实施规范 |

## Execution Log

| 日期 | 事件 | 详情 |
|------|------|------|
| 2026-03-05 | 设计调研 | 抓取 binance.com / web3.binance.com CSS 变量、字体、组件规格 |
| 2026-03-05 | 规范完成 | 输出 `docs/DESIGN-SPEC.md`（Dark Midnight 主题完整设计系统） |
| 2026-03-05 | Issue 创建 | 5 Phase + 22 AC + EXIT Gate |
| 2026-03-05 | Phase 1-5 实施 | style.css 全量重写 (415→509 行)：51+ CSS 变量、组件样式迁移、Badge 透明化、Binance 色阶 |
| 2026-03-05 | 字体引入 | index.html 添加 Google Fonts link (DM Sans + Noto Sans SC) |
| 2026-03-05 | JS 色值迁移 | app.js 添加 getCssVar() helper，替换 14 处硬编码色值，更新 PROVIDER_COLORS |
| 2026-03-05 | 自动化验证 | Playwright 测试 3 viewport (375/768/1440px)：0 JS error、0 溢出、色值校验通过 |
| 2026-03-05 | 修复 | 375px 溢出修复 (summary-table-container overflow-x:auto)、stale var(--text-muted) 修复 |
| 2026-03-05 | Oracle 审核 | Oracle R1 + R2 均因 token 上限无法输出结果（同 ISSUE-003 历史问题）；已通过自动化验证全量覆盖 22 AC |
