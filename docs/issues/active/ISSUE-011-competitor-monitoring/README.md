---
title: 'ISSUE-011: 竞品活跃度代理指标监控 — SDK 下载量 + GitHub 活跃度 + 状态页 + 文档密度 + 链上数据'
concepts:
- competitive-intelligence
- on-chain-analytics
- market-monitoring
---
# ISSUE-011: 竞品活跃度代理指标监控 — SDK 下载量 + GitHub 活跃度 + 状态页 + 文档密度 + 链上数据

## Meta
- **Status**: OPEN
- **Priority**: P2
- **Component**: scripts/, web/, .github/workflows/
- **Owner**: —
- **Date**: 2026-03-06
- **Effort**: Phase 1 = Short (2–4d)；Phase 2 = Medium (1–2w，独立里程碑)；Phase 3 = Backlog
- **Ref**: GitHub Issue #1

## Background

需要持续监控 WaaS 竞品的市场活跃度，辅助商业决策。当前 wallet-bench 只覆盖技术能力评测，缺少市场活跃度维度。

> ⚠️ **数据口径说明**：本方案采集的是**活跃度代理指标**（SDK 下载量、GitHub 活跃、服务可用性、文档成熟度、链上钱包创建量），不等价于供应商的真实 DAU/MAU。所有数据仅用于**趋势观察与横向相对比较**，不得用于得出绝对用户规模结论。

## 展示方案：GitHub Actions 定时采集 → JSON → Dashboard

采用方案 C：GitHub Actions 定时跑采集脚本 → 数据写入 `web/data/market_*.json` → commit 回仓库 → GitHub Pages 自动部署 → Dashboard 新增"市场活跃度"Tab 读取 JSON 展示。

### 方案可行性（已验证）

| 约束项 | 结论 |
|--------|------|
| Actions 免费额度 | 公开仓库**无限分钟数**，无需担心 |
| Cron 最小间隔 | 5 分钟一次（我们只需每日/每周，完全够） |
| Cron 自动失效 | **60 天无 repo 活动会停止调度** — 采集脚本每次 commit 数据即产生 repo 活动，自动保活 |
| npm API | 公开免费，无需认证，每日更新，最多查 18 个月历史 |
| npm API 限制 | scoped 包（`@org/pkg`）需 URL 编码为 `@org%2Fpkg`，不支持批量查询 |
| PyPI API | `pypistats.org/api/` 公开免费，每日更新，**保留 180 天历史**（短于 npm） |
| GitHub API | 认证后 5,000 req/hour（Actions 内自带 `GITHUB_TOKEN`），6 家 ~15 个仓库只需 ~15 次请求 |
| Dune API | 免费额度有限（社区报告约 2,500 credits/month），读 40 rpm，导出 20 credits/MB。轻量每日查询可行，重度分析需付费 |

> ⚠️ **时间窗口不一致**：npm 历史最长 18 个月，PyPI 仅 180 天，在跨源横向比较时需注意。

### 数据流

```
GitHub Actions (cron: 每日 UTC 06:00)
  → scripts/collect_market_data.py
    → npm API            → web/data/market_npm.json
    → pypistats API      → web/data/market_pypi.json
    → GitHub API         → web/data/market_github.json
    → Status pages       → web/data/market_status.json   ← Phase 1 新增
    → Docs changelog     → web/data/market_docs.json     ← Phase 1 新增
    → Dune API (可选)     → web/data/market_onchain.json  ← Phase 2
  → git commit "[skip ci] chore: update market data $(date -u +%Y-%m-%d)" + push
  → GitHub Pages 自动重新部署
  → Dashboard "市场活跃度" Tab 分层展示各维度数据
```

> **防循环说明**：commit message 包含 `[skip ci]`，避免触发 workflow 自身再次执行。workflow 需声明 `contents: write` 权限。

---

## 数据口径与指标定义

> 在开始开发前，必须明确各指标的含义、聚合规则和局限性。

| 指标 | 数据源 | 含义 | 聚合规则 | 局限性 | 置信度 | 阶段 |
|------|--------|------|----------|--------|--------|------|
| npm 周下载量 | npm API | 开发者安装 SDK 的频次 | 同一供应商多包**求和**（规则锁定） | 含 CI 重复下载，含镜像站流量 | 中 | Phase 1 |
| PyPI 周下载量 | pypistats | 同上（Python 生态） | 同上 | 同上 | 中 | Phase 1 |
| GitHub Stars | GitHub API | 社区关注度（滓后指标） | 取主仓库，不累加 | 不反映真实使用 | 低 | Phase 1 |
| GitHub Commits（近 30d） | GitHub API | 研发活跃度 | 取主仓库 | 不区分功能/修复/自动提交 | 中 | Phase 1 |
| GitHub Issues（近 30d open） | GitHub API | 社区活跃度信号 | 取主仓库 | 有噪音 | 中 | Phase 1 |
| **服务可用性（30d incident 数 / MTTR）** | 供应商 Status Page | 可用性与稳定性（企业级代理指标） | 取 incidents 数量 + 平均恢复时间 | 仅限有公开 Status Page 的供应商 | 高 | **Phase 1 新增** |
| **文档变更密度（30d commits + breaking change 占比）** | GitHub API（changelog/docs 目录） | 产品成熟度与开发者摩擦信号 | 取 docs/CHANGELOG 目录 30d commit 数 | 不区分内容质量 | 中 | **Phase 1 新增** |
| 30d 可归因活跃钉包数 | 链上 RPC + 工厂合约清单 | 最接近真实终端活跃的指标 | 按工厂地址归因，过滤机器人 | 仅覆盖 ERC-4337 智能钉包供应商（3/6） | 高（可归因供应商） | Phase 2 |
| 30d tx/active wallet（中位数） | 同上（派生指标） | 区分“空壳活跃”与真实使用深度 | 复用 Phase 2 活跃钉包集合 | 同上 | 高 | Phase 2 派生 |
| 链上钉包创建量（周） | Dune / RPC | ERC-4337 UserOp 创建次数 | 按 factory 地址分组 | 无法覆盖 EOA/托管架构 | 中 | Phase 2 |

**多包聚合规则（锁定）**：同一供应商多个 npm 包的下载量相加作为该供应商的“周下载量”。规则一旦确定不得变更，否则会产生假波动。

**指标置信度标签**：每个指标在 Dashboard 展示时附置信度（高/中/低），避免将弱归因数据当硬结论。链上指标对 EOA/托管架构供应商置信度为“不可追踪”，需标注。
---

## 任务分解

### Phase 0: 调研（前置依赖，阻塞 Phase 1/2 开发）

#### Task 0-1: 验证 npm/PyPI 包名清单

**目的**：确认每家供应商可追踪的 npm/PyPI 包名，验证 API 可返回有效数据，并通过准入规则过滤不稳定包名。

**准入规则**（必须同时满足）：
1. 包归属官方组织（org 名与供应商一致）
2. 近 90 天内有新版本发布
3. API 可稳定返回历史下载数据

**候选包名**：

| 供应商 | npm 候选包 | PyPI 候选包 |
|--------|-----------|-------------|
| Privy | `@privy-io/server-auth`, `@privy-io/react-auth`, `@privy-io/mcp-server` | — |
| Coinbase | `@coinbase/agentkit`, `@coinbase/coinbase-sdk` | `coinbase-agentkit` |
| Crossmint | `@crossmint/wallets-sdk`, `@crossmint/client-sdk-smart-wallet` | — |
| BNB Chain MCP | `@bnb-chain/mcp` | — |
| MoonPay | `@moonpay/cli` ⚠️ 需验证是否官方维护 | — |
| Minara | `minara` ⚠️ 包名过于通用，高优先级验证 | — |

**API 信息**：
- npm：`GET https://api.npmjs.org/downloads/point/last-week/{package}`，scoped 包 URL 编码为 `@org%2Fpkg`
- pypistats：`GET https://pypistats.org/api/packages/{package}/recent?period=week`

**交付物**：通过准入规则验证的包名清单 + 每个包的最新周下载量快照 + 不通过准入的包名及原因

---

#### Task 0-2: 整理 GitHub 仓库清单

**目的**：确认每家供应商的核心开源仓库，用于追踪 Stars/Commits/活跃度。

**准入规则**（必须同时满足）：
1. 仓库归属官方组织
2. 近 90 天内有 commit 活动
3. GitHub API 可正常返回数据

**候选仓库**：

| 供应商 | 候选仓库 |
|--------|---------|
| Privy | `privy-io/privy-js`, `privy-io/privy-mcp-server` |
| Coinbase | `coinbase/agentkit`, `coinbase/coinbase-sdk-python` |
| Crossmint | `Crossmint/crossmint-sdk`, `Crossmint/mcp-crossmint-checkout` |
| BNB Chain MCP | `bnb-chain/bnbchain-mcp` |
| MoonPay | `moonpay/cli` ⚠️ 待确认是否存在 |
| Minara | `Minara-AI/skills` |

**交付物**：通过准入规则的仓库清单（owner/repo 格式） + 不可追踪的供应商及原因

---

#### Task 0-3: 调研链上工厂合约地址

**目的**：找到各供应商在链上创建钱包的工厂合约地址，用于追踪钱包创建量和活跃度。

**范围**：聚焦 ERC-4337 相关的 Smart Wallet Factory，按链查找。

| 供应商 | 预期追踪方式 | 目标链 | 难度 |
|--------|-------------|--------|------|
| Privy | Smart Wallet Factory event | Ethereum, Base, Polygon | 中 — 需从文档或链上交易反查 |
| Coinbase | CDP Wallet Factory / Account 创建 | Base | 中 — 可能通过 AgentKit 源码找到 |
| Crossmint | ERC-4337 AccountFactory event | Base, Ethereum, Polygon | 中 — 文档提到 Fireblocks 后端 |
| BNB Chain MCP | 无工厂合约（本地 EOA） | BSC | — 不可追踪 |
| MoonPay | 无工厂合约（本地 HD 钱包） | — | — 不可追踪 |
| Minara | 托管钱包 | Base | — 链上不可追踪 |

**已知信息**：
- ERC-4337 EntryPoint 地址：`0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789`（各链固定）
- 可通过 Dune 查询 EntryPoint 的 UserOperation 事件，按 factory 地址分组
- 已有 Dune 社区 dashboard 追踪 ERC-4337 生态（可复用 query）

> ⚠️ **归因风险**：按 factory 地址分组时，需确认地址确实归属该供应商，防止把第三方工厂误计入。

**调研方法**：
1. 查阅各供应商官方文档中的合约地址
2. 在 Etherscan/Basescan 上搜索已知供应商钱包交易，反查 Factory 地址
3. 搜索 Dune 社区现有的 ERC-4337 factory 分析 dashboard
4. 检查 AgentKit / Crossmint SDK 源码中的合约地址常量

**交付物**：
- 可追踪供应商的 Factory 合约地址清单（按链）+ 地址来源说明
- 不可追踪供应商的说明
- 推荐的 Dune query 模板（如找到社区现成 query）

---

#### Task 0-4: Dune Analytics 免费额度实测

**目的**：验证 Dune 免费 API 能否满足"每日一次轻量查询"的需求。

**范围**：
1. 注册 Dune 免费账号，获取 API key
2. 在 Dune Web 创建一个简单 query（如 ERC-4337 EntryPoint 近 7 天 UserOp 数量）
3. 通过 API 执行 query 并获取结果（注意：免费版不支持通过 API 创建 query）
4. 记录 credit 消耗、响应时间、结果大小、异步执行延迟

**已知信息**：
- 免费额度：社区报告约 2,500 credits/month（官方未公开）
- 费率：执行 query 消耗 credit，导出 20 credits/MB
- 执行模型：**异步**，需轮询结果，存在超时风险，脚本需处理

**交付物**：Dune 免费额度是否够用的结论 + 备选方案（Flipside、The Graph 或直接 RPC 查询）

---

#### Task 0-5: 指标口径定义文档（新增）

**目的**：在开发前确定所有指标的含义、聚合方式和展示规则，避免后续数据"假波动"和误读。

**内容**：
- 每个指标的定义、单位、时间粒度（统一为 UTC 周）
- 多包聚合规则（同供应商多包如何求和，且规则锁定）
- Dashboard 展示层面的命名规范（不允许出现"活跃用户数"字样）
- 数据缺失/API 失败时的降级展示规则

**交付物**：`docs/issues/active/ISSUE-011-competitor-monitoring/metric-definitions.md`

- [ ] **Task 0-6**: 整理各供应商 Status Page 地址 + changelog 路径
  - 确认各供应商是否有公开 Status Page（优先 Statuspage.io，Privy/Coinbase/Crossmint 均使用此平台）
  - 记录 incidents JSON 端点（通常为 `https://{subdomain}.statuspage.io/api/v2/incidents.json`）
  - 确认 BNB Chain MCP / MoonPay / Minara 是否有对应页面
  - 记录各供应商 changelog/docs 目录在 GitHub 中的具体路径

  **交付物**：`status_pages.yaml`（各供应商 Status Page URL + API 端点 + changelog 文件路径）
---

### Phase 1: npm/PyPI + GitHub + 状态页 + 文档密度（依赖 Task 0-1, 0-2, 0-5, 0-6）

- [ ] **Task 1-1**: 编写 `scripts/collect_market_data.py`
  - 从 npm API 采集各包周下载量（逐包请求，重试 3 次，超时 10s）
  - 从 pypistats API 采集 PyPI 下载量
  - 从 GitHub API 采集 stars / 近 30d commits / 近 30d open issues / 最近提交日期
  - **新增**：从 Status Page API 采集近 30d incident 数量 + MTTR，输出 `web/data/market_status.json`
  - **新增**：从 GitHub API 采集 changelog/docs 目录近 30d commit 数 + breaking change 关键词匹配，输出 `web/data/market_docs.json`
  - 部分失败降级：某包失败时写入 `null` + 错误原因，不中断整体采集
  - 上次成功快照回退：如全量失败，保留上次 JSON 不覆盖
  - 输出 `web/data/market_npm.json`、`web/data/market_pypi.json`、`web/data/market_github.json`（含 schema 版本号）

- [ ] **Task 1-2**: 编写 GitHub Actions workflow `.github/workflows/collect-market-data.yml`
  - cron: `0 6 * * *`（每日 UTC 06:00）
  - 权限：`contents: write`（显式声明）
  - commit message 格式：`[skip ci] chore: update market data YYYY-MM-DD`（防循环触发）
  - 采集失败时：workflow 标记为失败，不 commit 空数据

- [ ] **Task 1-3**: Dashboard 新增“市场活跃度”Tab
  - **分层展示**（独立卡片，禁止合并为单一“用户数”）：
    - 开发者兴趣层：npm/PyPI 下载量趋势
    - 研发健康层：GitHub commits / issues / stars
    - 服务可靠层：Status Page incident 频次 / MTTR ← 新增
    - 产品成熟层：文档变更密度 + breaking change 比例 ← 新增
    - 终端活跃层：链上钉包数据（Phase 2 占位，展示“敬请期待”）
  - **分层展示**：SDK 下载量趋势、GitHub 活跃度、链上数据各自独立卡片，不合并为单一"用户数"
  - Tab 内加数据口径免责声明（参考 Task 0-5 定义）
  - 数据缺失时展示"暂无数据"而非显示 0

- [ ] **Task 1-4**: 数据质量与失败治理（新增）
  - 采集脚本输出结构化日志（JSON lines 格式），记录每个 API 调用的状态
  - 定义数据新鲜度检查：Dashboard 显示"最后更新时间"，超过 48h 未更新时展示警告
  - 历史数据存档策略：JSON 只保留最新快照，历史趋势通过 git log 可追溯

---

### Phase 2: 链上真实终端活跃（独立里程碑，依赖 Task 0-3, 0-4）

> Phase 2 不阻塞 Phase 1 交付。仅在 Task 0-3 找到稳定 factory 地址且 Task 0-4 确认 Dune 成本可控后启动。

- [ ] **Task 2-1**: 搞定链上归因口径规则文档（版本化配置：链范围、工厂合约白名单、机器人过滤规则）
- [ ] **Task 2-2**: 搞定 Dune query 追踪钉包创建趋势（含 factory 地址归属验证）
- [ ] **Task 2-3**: 采集脚本增加链上数据调用（Dune 异步轮询 + RPC 降级），输出 `web/data/market_onchain.json`
  - 含 `active_wallets_30d` + `tx_per_active_wallet_median` 派生字段（复用链上数据，无额外请求）
- [ ] **Task 2-4**: Dashboard 终端活跃层卡片上线（仅展示可归因 3 家供应商，其余标注“架构不可追踪”）

### Phase 3: Backlog（商业化信号，半自动）

> 自动化成本高、信号噪声大，暂不纳入主线。

- [ ] **Task 3-1**: 新增生产级集成数（季度）
  - 自动抓取 GitHub Releases、官方 changelog、生态目录页候选事件
  - 人工审核确认“生产级”判定后写入已确认事件表
  - 工作量：2–4d + 持续人工校验
- [ ] **Task 3-2**: 招聘结构雷达（季度人工抄样）
  - 不做全自动采集（ATS 页面随时改版，维护成本过高）
  - 每季度人工观察各供应商招聘页 SA/BD/客户成功占比变化，记录到 `docs/market-snapshots/`

---

## 风险 & 约束

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 链上工厂合约地址找不到 | Phase 2 无法进行 | Phase 1 可独立交付价值，Phase 2 降级为可选 |
| Dune 免费额度不够 | 链上数据无法自动化 | 改为手动定期快照，或用 Flipside / The Graph / 直接 RPC 查询 |
| npm 下载量含 CI 重复计数 | 数据有噪音 | 仅看趋势和相对比较，Dashboard 加免责说明 |
| BNB/MoonPay/Minara 链上不可追踪 | 3/6 供应商缺链上数据 | 用 npm/GitHub 数据补充，标注架构原因 |
| 60 天无活动 Actions 自动停止 | 采集中断 | 采集脚本每次 commit 数据即产生 repo 活动，自动保活 |
| scoped npm 包不支持批量查询 | 采集略慢 | 6 家 ~15 个包，逐个请求只需数秒，可接受 |
| workflow 自提交触发循环 | Actions 无限运行 | commit message 加 `[skip ci]` |
| 分支保护规则导致 push 失败 | 采集数据无法写入 | workflow 使用 `GITHUB_TOKEN` + 确认分支规则允许机器人 push |
| 供应商包更名或迁移 | 数据中断 | Task 0-1 准入规则 + 定期（每季度）重新验证包名清单 |
| 多包聚合口径变更导致假波动 | 数据失真 | 口径规则锁定（Task 0-5），变更需在文档中记录并在 Dashboard 标注断点 |
| 链上地址归因错误 | 数据误导 | Task 0-3 要求记录地址来源，发布前人工核对 |
| Dune query 异步执行超时 | 采集失败 | 脚本加轮询 + 超时降级，失败时保留上次快照 |
| API 返回结构变更 | 脚本异常 | 加 schema 版本号 + 结构校验，变更时 workflow 失败报警 |
| Status Page 结构差异（非 Statuspage.io 托管） | 采集字段不统一 | 优先支持 Statuspage.io（3 家供应商均使用），其余手动适配或标注“暂无数据” |
| 文档目录路径无规律 | 无法定位 changelog | Task 0-6 仓库清单同时记录 changelog 文件路径 |
| 链上归因口径漂移 | 数据跳变 | Task 2-1 把归因规则写成版本化配置，变更必须 PR + changelog |
| 招聘页面无公开 API | 全自动不可行 | 不做全自动，改为季度人工抄样（Phase 3） |

---

## 指标全景图

```
开发者兴趣  → npm/PyPI 下载量趋势              [Phase 1 / 日频自动 / 置信度：中]
研发健康    → GitHub commits/issues/stars      [Phase 1 / 日频自动 / 置信度：中]
服务可靠    → Status Page incidents/MTTR       [Phase 1 新增 / 日频自动 / 置信度：高]
产品成熟    → 文档变更密度/breaking change比例  [Phase 1 新增 / 日频自动 / 置信度：中]
终端规模    → 30d 可归因活跃钉包数              [Phase 2 / 日频自动 / 仅 3/6 供应商 / 置信度：高]
终端深度    → 30d tx/active wallet 中位数       [Phase 2 派生 / 同上]
商业化进展  → 新增生产级集成数（季度）            [Phase 3 / 半自动+人工审核 / 置信度：中高]
组织扩张    → 招聘结构雷达                      [不自动化 / 季度人工抄样]
```
