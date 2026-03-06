# wallet-bench 设计规范 (Binance Style)

> **目标**：将 wallet-bench 前端视觉风格对齐 Binance 官网（Dark Midnight 主题），打造专业、数据密集、高辨识度的 benchmark 展示平台。
>
> **状态**：Draft v1 — 待评审后新起 Issue 实施
>
> **参考来源**：binance.com、web3.binance.com、Binance Markets 页面 CSS 变量抓取

---

## 1. 设计原则

| 原则 | 说明 |
|------|------|
| **暗色优先** | 以纯黑为底，通过亮度阶梯（而非阴影）建立层级 |
| **颜色即数据** | 绿/红仅用于 pass/fail，黄仅用于品牌强调，绝不做装饰用 |
| **数据密度可调** | 矩阵/表格追求高密度（紧凑行高、小字号），概览卡片用大留白 |
| **一致性语义 Token** | 所有颜色、间距、圆角通过 CSS 变量引用，不硬编码 |
| **渐进披露** | 首屏只展示关键对比，详情通过点击/展开呈现 |

---

## 2. 色彩系统（Dark Midnight 主题）

### 2.1 背景层级

从深到浅共 7 级，通过纯灰度建立空间层次：

| 层级 | CSS 变量 | 色值 | 用途 |
|------|---------|------|------|
| L0 | `--bg-base` | `#000000` | 页面底色 |
| L1 | `--bg-subtle` | `#111111` | 交替背景（表格奇数行等） |
| L2 | `--bg-card` | `#1A1A1A` | 卡片、面板 |
| L3 | `--bg-input` | `#222222` | 输入框、代码块 |
| L4 | `--bg-elevated` | `#333333` | 弹窗、Tooltip、hover 态 |
| L5 | `--bg-border` | `#3D3D3D` | 分割线、网格线 |
| L6 | `--bg-muted` | `#4F4F4F` | 标签背景、禁用按钮 |

### 2.2 文字层级

| CSS 变量 | 色值 | 用途 |
|---------|------|------|
| `--text-primary` | `#FFFFFF` | 主要正文 |
| `--text-secondary` | `#9C9C9C` | 次要文字、表头 |
| `--text-tertiary` | `#7D7D7D` | 辅助文字、图标 |
| `--text-disabled` | `#5B5B5B` | 禁用态文字 |
| `--text-on-yellow` | `#000000` | 黄色按钮上的文字 |
| `--text-on-gray` | `#EDEDED` | 灰色表面上的文字 |
| `--text-emphasis` | `#FF693D` | 强调/告警（橙色） |

### 2.3 品牌色（黄色系）

| CSS 变量 | 色值 | 用途 |
|---------|------|------|
| `--brand-yellow` | `#F0B90B` | 链接、强调色、选中态 |
| `--brand-yellow-btn` | `#FCD535` | 主 CTA 按钮背景 |
| `--brand-yellow-alpha-10` | `rgba(252, 213, 53, 0.15)` | 黄色浅底（badge 背景） |
| `--brand-yellow-alpha-20` | `rgba(252, 213, 53, 0.2)` | 黄色中底（hover） |

### 2.4 语义色（状态/结果）

| CSS 变量 | 色值 | 用途 |
|---------|------|------|
| `--color-pass` | `#28A473` | 通过/成功/买入 |
| `--color-pass-hover` | `#2EBD85` | 通过悬停态 |
| `--color-pass-bg` | `#102821` | 通过浅底（深色青绿） |
| `--color-pass-alpha` | `rgba(40, 164, 115, 0.2)` | 通过透明底 |
| `--color-fail` | `#F63C55` | 失败/错误/卖出 |
| `--color-fail-hover` | `#F6465D` | 失败悬停态 |
| `--color-fail-bg` | `#35141D` | 失败浅底（深色暗红） |
| `--color-fail-alpha` | `rgba(246, 60, 85, 0.2)` | 失败透明底 |
| `--color-skip` | `#F0B90B` | 跳过/警告（复用品牌黄） |
| `--color-skip-alpha` | `rgba(240, 185, 11, 0.1)` | 跳过透明底 |

### 2.5 遮罩与玻璃效果

| CSS 变量 | 色值 | 用途 |
|---------|------|------|
| `--overlay-mask` | `rgba(0, 0, 0, 0.6)` | 模态遮罩 |
| `--overlay-glass` | `rgba(255, 255, 255, 0.08)` | 毛玻璃/浮层 |

---

## 3. 字体系统

### 3.1 字体栈

由于 BinanceNova 为私有字体，wallet-bench 使用以下近似替代：

```css
--font-display: "DM Sans", "Noto Sans SC", sans-serif;
--font-body: "DM Sans", "Noto Sans SC", sans-serif;
--font-mono: "JetBrains Mono", "SF Mono", "Fira Code", monospace;
```

> **说明**：DM Sans 是 Google Fonts 上与 BinanceNova 几何风格最接近的免费字体。中文回退用 Noto Sans SC。
> 通过 `<link>` 引入：`https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap`

### 3.2 字号/字重体系

| 角色 | 大小 | 行高 | 字重 | 用途 |
|------|------|------|------|------|
| Display | 36px | 1.2 | 700 | 页面标题 `wallet-bench` |
| H1 | 24px | 1.3 | 600 | Tab 区域标题 |
| H2 | 18px | 1.4 | 600 | 子区域标题 |
| H3 | 15px | 1.4 | 600 | 卡片标题 |
| Body | 14px | 1.5 | 400 | 正文、表格单元格 |
| Caption | 12px | 1.5 | 400 | 辅助文字、表头、badge |
| Mono | 13px | 1.5 | 400 | 地址、hash、代码 |

---

## 4. 间距系统

采用 4px 基础单位的间距阶梯：

| Token | 值 | 用途 |
|-------|-----|------|
| `--space-2xs` | `4px` | 图标与文字间距、badge 内边距 |
| `--space-xs` | `8px` | 紧凑元素间距 |
| `--space-s` | `12px` | 表格单元格内边距（垂直） |
| `--space-m` | `16px` | 表格单元格内边距（水平）、卡片间距 |
| `--space-l` | `20px` | 区块间距 |
| `--space-xl` | `24px` | 大区块间距、页面边距 |
| `--space-2xl` | `32px` | 节间距 |
| `--space-3xl` | `48px` | 大节间距 |
| `--space-4xl` | `64px` | 页面顶部/底部留白 |

**表格单元格标准**：`padding: 12px 16px`（与 Binance Markets 一致）

---

## 5. 圆角系统

| Token | 值 | 用途 |
|-------|-----|------|
| `--radius-xs` | `4px` | 小标签、输入框 |
| `--radius-s` | `6px` | 按钮、badge |
| `--radius-m` | `8px` | 子选项卡 |
| `--radius-l` | `12px` | 卡片 |
| `--radius-xl` | `16px` | 大卡片、面板 |
| `--radius-pill` | `100px` | 药丸型 badge |
| `--radius-circle` | `50%` | 圆形头像/图标 |

---

## 6. 组件规范

### 6.1 页面头部 (Header)

```
┌──────────────────────────────────────────────────────┐
│  wallet-bench    副标题                    [刷新数据]  │
│  ─────────────────────────────────────────────────── │
│  [密钥与签名架构]  [Agent Skill 体验]                  │
└──────────────────────────────────────────────────────┘
```

| 属性 | 值 |
|------|-----|
| 标题字号 | 24px, weight 700 |
| 副标题 | 14px, `--text-secondary` |
| 背景 | `--bg-base` (#000000) |
| 下边框 | `1px solid --bg-border` (#3D3D3D) |
| 内边距 | `16px 24px` |
| position | `sticky`, `top: 0`, `z-index: 999` |

### 6.2 主选项卡 (Primary Tabs)

| 属性 | 值 |
|------|-----|
| 字号 | 15px, weight 500 |
| 默认色 | `--text-tertiary` (#7D7D7D) |
| 选中色 | `--brand-yellow` (#F0B90B) |
| 选中下划线 | `2px solid --brand-yellow` |
| hover | `--text-primary` (#FFFFFF) |
| 间距 | `padding: 12px 20px` |
| 容器下边框 | `1px solid --bg-border` |

### 6.3 子选项卡 (Sub Tabs)

| 属性 | 值 |
|------|-----|
| 字号 | 13px, weight 400 |
| 默认态 | `--bg-card` (#1A1A1A) 底, `--text-secondary` 文字 |
| 选中态 | `--brand-yellow-alpha-10` 底, `--brand-yellow` 文字 |
| hover | `--bg-elevated` (#333333) |
| 圆角 | `--radius-s` (6px) |
| 间距 | `padding: 6px 14px`, gap `8px` |

### 6.4 数据表格 (Data Table)

这是 wallet-bench 最核心的组件，直接参考 Binance Markets 表格。

| 属性 | 值 |
|------|-----|
| 背景 | 透明（继承 `--bg-base`） |
| 表头背景 | `--bg-card` (#1A1A1A) |
| 表头文字 | 12px, `--text-tertiary` (#7D7D7D), weight 400 |
| 表体文字 | 14px, `--text-primary` (#FFFFFF), weight 400 |
| 行高度 | `52px`（含 padding） |
| 单元格 padding | `12px 16px` |
| 行分割线 | `1px solid --bg-border` (#3D3D3D) |
| hover 行 | `--bg-card` (#1A1A1A) |
| 排序图标 | SVG 箭头, 12px |
| 固定列阴影 | `box-shadow: inset -10px 0 8px -8px rgba(0,0,0,0.3)` |
| 状态 pass | `--color-pass` (#28A473) |
| 状态 fail | `--color-fail` (#F63C55) |
| 状态 skip | `--color-skip` (#F0B90B) |
| 延迟 badge | 12px, `--text-tertiary`, monospace |

**功能矩阵特殊规则**：
- 第一列（测试项名）左对齐，font-weight 500
- 其余列居中
- 通过/失败用纯色文字+图标，不用背景色
- provider 列头可点击，hover 变 `--brand-yellow`

### 6.5 卡片 (Card)

| 属性 | 值 |
|------|-----|
| 背景 | `--bg-card` (#1A1A1A) |
| 边框 | `1px solid --bg-border` (#3D3D3D) |
| 圆角 | `--radius-l` (12px) |
| 内边距 | `20px 24px` |
| hover | 边框变 `--bg-muted` (#4F4F4F), 无阴影 |
| 标题 | 15px, weight 600, `--text-primary` |
| 描述 | 14px, weight 400, `--text-secondary` |

### 6.6 架构类别 Badge

| 类别 | 背景 | 文字 | 圆角 |
|------|------|------|------|
| Local | `rgba(40, 164, 115, 0.2)` | `#28A473` | pill (100px) |
| TEE | `rgba(88, 166, 255, 0.2)` | `#58A6FF` | pill |
| Intent | `rgba(240, 185, 11, 0.15)` | `#F0B90B` | pill |
| MPC+AA | `rgba(187, 128, 255, 0.2)` | `#BB80FF` | pill |
| Unknown | `--bg-muted` (#4F4F4F) | `--text-secondary` | pill |

**规则**：badge 用透明底+同色文字（Binance 风格），而非实色底+黑字。

### 6.7 按钮 (Button)

| 变体 | 背景 | 文字 | 边框 | 圆角 |
|------|------|------|------|------|
| Primary (CTA) | `--brand-yellow-btn` (#FCD535) | `--text-on-yellow` (#000) | none | 8px |
| Secondary | `--bg-elevated` (#333333) | `--text-primary` (#FFF) | none | 8px |
| Ghost | transparent | `--text-secondary` | `1px solid --bg-border` | 8px |
| Link | transparent | `--brand-yellow` | none | — |
| Disabled | `--bg-elevated` (#333333) | `--text-disabled` (#5B5B5B) | none | 8px |

**按钮尺寸**：
- Default: `height: 40px`, `padding: 0 16px`, font 14px weight 500
- Small: `height: 32px`, `padding: 0 12px`, font 13px weight 500

### 6.8 雷达图 (Radar Chart)

| 属性 | 值 |
|------|-----|
| 网格线 | `--bg-border` (#3D3D3D) |
| 轴标签 | 12px, `--text-tertiary` (#7D7D7D) |
| 数据线 | 各 provider 对应色（见 Provider 调色板） |
| 填充 | 对应色 20% 透明度 |
| 数据点 | 3px 实心圆 |
| 卡片底 | `--bg-card` (#1A1A1A) |

### 6.9 热力图 (Heatmap)

| 属性 | 值 |
|------|-----|
| 快（<500ms） | `hsl(160, 60%, 35%)` — 偏 Binance 绿 |
| 中（500-2000ms） | `hsl(45, 80%, 45%)` — 偏 Binance 黄 |
| 慢（>2000ms） | `hsl(0, 70%, 45%)` — 偏 Binance 红 |
| 色条 | linear-gradient 三段式 |
| 无数据 | `--bg-border` (#3D3D3D), `--text-disabled` |

### 6.10 柱状图 (Bar Chart)

| 属性 | 值 |
|------|-----|
| 柱体颜色 | `--brand-yellow` (#F0B90B) |
| 柱体高度 | 16px |
| 柱体圆角 | 3px |
| 背景轨道 | `--bg-card` (#1A1A1A) |
| 标签 | 13px, `--text-secondary`, 右对齐 |
| 数值 | 13px, weight 600, `--text-primary` |

### 6.11 评分条 (Score Bar)

| 属性 | 值 |
|------|-----|
| 轨道背景 | `--bg-border` (#3D3D3D) |
| 轨道高度 | 6px |
| 圆角 | 3px |
| 填充色 | 由分数映射 hue (120°绿 → 0°红) |
| 标签 | 12px, `--text-secondary` |

### 6.12 折叠面板 (Collapsible / Accordion)

| 属性 | 值 |
|------|-----|
| 背景 | `--bg-card` (#1A1A1A) |
| 边框 | `1px solid --bg-border` |
| 圆角 | `--radius-l` (12px) |
| summary padding | `16px 20px` |
| summary 字号 | 15px, weight 600 |
| 展开指示器 | `▶` 旋转 90°, `--text-tertiary` |
| 内容 padding | `20px` |
| 展开时 summary | 下边框 `--bg-border` |

### 6.13 详情页 (Detail Page)

| 属性 | 值 |
|------|-----|
| 返回按钮 | Ghost 风格, `--brand-yellow` 文字 |
| 属性卡片网格 | `grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))` |
| 属性卡片 | `--bg-card` 底, 12px 圆角, 16px 内边距 |
| 属性标题 | 12px, `--text-tertiary`, weight 400 |
| 属性值 | 14px, `--text-primary`, weight 500 |
| Tag (链名/能力) | `--bg-input` (#222222) 底, 12px padding, pill 圆角 |

### 6.14 Footer

| 属性 | 值 |
|------|-----|
| 上边框 | `1px solid --bg-border` |
| 文字 | 12px, `--text-tertiary` |
| 上方间距 | `--space-3xl` (48px) |
| 内边距 | `16px 0` |
| 对齐 | 居中 |

---

## 7. Provider 调色板

每个 provider 有一个专属色（用于雷达图、图表等多 provider 对比场景）：

| Provider | 主色 | 填充色 (20% alpha) |
|----------|------|-------------------|
| BNB Chain MCP | `#F0B90B` | `rgba(240, 185, 11, 0.2)` |
| Crossmint | `#6C5CE7` | `rgba(108, 92, 231, 0.2)` |
| Privy | `#58A6FF` | `rgba(88, 166, 255, 0.2)` |
| Coinbase AgentKit | `#4285F4` | `rgba(66, 133, 244, 0.2)` |
| MoonPay Agents | `#7B61FF` | `rgba(123, 97, 255, 0.2)` |
| Minara AI | `#28A473` | `rgba(40, 164, 115, 0.2)` |

---

## 8. 动画与过渡

| 场景 | 属性 | 时长 | 缓动 |
|------|------|------|------|
| 按钮 hover | `background, border-color` | `150ms` | `ease` |
| 表格行 hover | `background` | `200ms` | `ease` |
| Tab 切换 | `color, border-color` | `150ms` | `ease` |
| 折叠展开 | `transform (▶)` | `200ms` | `ease` |
| 页面加载 | `opacity` | `300ms` | `ease-out` |

**原则**：动画克制、功能性为主。不使用弹跳、过度缩放等花哨效果。

---

## 9. 布局系统

### 9.1 页面容器

```css
max-width: 1248px;  /* Binance 标准内容宽度 */
margin: 0 auto;
padding: 0 24px;
```

### 9.2 响应式断点

| 断点 | 描述 |
|------|------|
| `≤768px` | 移动端：单列布局，padding 缩至 16px |
| `769-1080px` | 平板：双列网格 |
| `≥1081px` | 桌面端：完整多列布局 |

### 9.3 网格

```css
/* 卡片网格 */
grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
gap: 16px;

/* 并排图表 */
grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
gap: 24px;

/* 详情属性卡片 */
grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
gap: 12px;
```

---

## 10. 与现有设计的差异对照

| 项目 | 现有 (GitHub Dark) | 目标 (Binance Midnight) |
|------|-------------------|----------------------|
| 页面底色 | `#0d1117` (蓝灰调) | `#000000` (纯黑) |
| 卡片底色 | `#161b22` | `#1A1A1A` |
| 边框色 | `#30363d` | `#3D3D3D` |
| 强调色 | `#58a6ff` (蓝色) | `#F0B90B` (黄色) |
| 通过色 | `#3fb950` | `#28A473` |
| 失败色 | `#f85149` | `#F63C55` |
| 字体 | system-ui 系统默认 | DM Sans + Noto Sans SC |
| 表头 | 深色底+粗体 | 浅灰文字+普通字重 |
| Badge 样式 | 实色底+黑字 | 透明底+同色文字 |
| 按钮 CTA | 灰底+边框 | 黄底+黑字 |
| 表格密度 | 宽松 | 紧凑 (12px 16px padding) |
| 圆角 | 8px 统一 | 分级 (4-16px) |

---

## 11. 实施检查清单

实施时按以下顺序推进：

- [ ] **Phase 1: CSS 变量重构** — 将所有硬编码色值替换为本规范的 CSS 变量
- [ ] **Phase 2: 字体引入** — 添加 Google Fonts link, 替换 font-family
- [ ] **Phase 3: 色彩迁移** — 逐组件替换色值（bg → text → brand → semantic）
- [ ] **Phase 4: 组件精调** — 表格密度、badge 样式、按钮风格、tab 样式
- [ ] **Phase 5: 布局调整** — max-width 1248px, 间距阶梯, 响应式断点
- [ ] **Phase 6: 动画与细节** — 过渡动画、hover 效果、loading 状态
- [ ] **Phase 7: 验收** — 与 Binance 官网截图对比，确保视觉一致性

---

## 附录 A: CSS 变量完整清单（可直接粘贴到 style.css）

```css
:root {
  /* 背景层级 */
  --bg-base: #000000;
  --bg-subtle: #111111;
  --bg-card: #1A1A1A;
  --bg-input: #222222;
  --bg-elevated: #333333;
  --bg-border: #3D3D3D;
  --bg-muted: #4F4F4F;

  /* 文字层级 */
  --text-primary: #FFFFFF;
  --text-secondary: #9C9C9C;
  --text-tertiary: #7D7D7D;
  --text-disabled: #5B5B5B;
  --text-on-yellow: #000000;
  --text-on-gray: #EDEDED;
  --text-emphasis: #FF693D;

  /* 品牌色 */
  --brand-yellow: #F0B90B;
  --brand-yellow-btn: #FCD535;
  --brand-yellow-alpha-10: rgba(252, 213, 53, 0.15);
  --brand-yellow-alpha-20: rgba(252, 213, 53, 0.2);

  /* 语义色 — 通过/成功 */
  --color-pass: #28A473;
  --color-pass-hover: #2EBD85;
  --color-pass-bg: #102821;
  --color-pass-alpha: rgba(40, 164, 115, 0.2);

  /* 语义色 — 失败/错误 */
  --color-fail: #F63C55;
  --color-fail-hover: #F6465D;
  --color-fail-bg: #35141D;
  --color-fail-alpha: rgba(246, 60, 85, 0.2);

  /* 语义色 — 跳过/警告 */
  --color-skip: #F0B90B;
  --color-skip-alpha: rgba(240, 185, 11, 0.1);

  /* 遮罩 */
  --overlay-mask: rgba(0, 0, 0, 0.6);
  --overlay-glass: rgba(255, 255, 255, 0.08);

  /* 字体 */
  --font-display: "DM Sans", "Noto Sans SC", sans-serif;
  --font-body: "DM Sans", "Noto Sans SC", sans-serif;
  --font-mono: "JetBrains Mono", "SF Mono", "Fira Code", monospace;

  /* 间距 */
  --space-2xs: 4px;
  --space-xs: 8px;
  --space-s: 12px;
  --space-m: 16px;
  --space-l: 20px;
  --space-xl: 24px;
  --space-2xl: 32px;
  --space-3xl: 48px;
  --space-4xl: 64px;

  /* 圆角 */
  --radius-xs: 4px;
  --radius-s: 6px;
  --radius-m: 8px;
  --radius-l: 12px;
  --radius-xl: 16px;
  --radius-pill: 100px;
  --radius-circle: 50%;

  /* 动画 */
  --duration-fast: 150ms;
  --duration-base: 200ms;
  --duration-slow: 300ms;

  /* 布局 */
  --content-max-width: 1248px;

  /* z-index */
  --z-header: 999;
  --z-dropdown: 1200;
  --z-modal: 1200;
  --z-tooltip: 1400;
}
```

---

## 附录 B: Provider 色值 CSS 变量

```css
:root {
  --provider-bnb: #F0B90B;
  --provider-bnb-alpha: rgba(240, 185, 11, 0.2);
  --provider-crossmint: #6C5CE7;
  --provider-crossmint-alpha: rgba(108, 92, 231, 0.2);
  --provider-privy: #58A6FF;
  --provider-privy-alpha: rgba(88, 166, 255, 0.2);
  --provider-coinbase: #4285F4;
  --provider-coinbase-alpha: rgba(66, 133, 244, 0.2);
  --provider-moonpay: #7B61FF;
  --provider-moonpay-alpha: rgba(123, 97, 255, 0.2);
  --provider-minara: #28A473;
  --provider-minara-alpha: rgba(40, 164, 115, 0.2);
}
```
