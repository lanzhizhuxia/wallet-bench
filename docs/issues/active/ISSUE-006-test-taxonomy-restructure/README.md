---
title: 'ISSUE-006: 测试分类重构 — 基础设施 vs 应用层分离 + DeFi/Swap 新维度'
concepts:
- test-taxonomy
- infra-vs-app
- scoring-fairness
- filter-ux
- defi-swap-bridge
---
# ISSUE-006: 测试分类重构 — 基础设施 vs 应用层分离 + DeFi/Swap 新维度

## Meta
- **Status**: OPEN
- **Priority**: P1
- **Component**: wallet-bench / data model + web (app.js + style.css) + evaluations
- **Owner**: —
- **Date**: 2026-03-05
- **Effort**: Medium (1-2d)
- **Depends**: ISSUE-005（详情页 UX 增强基本完成后实施）
- **Source**: 用户分析 + Oracle 架构审查 (session `ses_3420aee8effe`)
- **Audience**: 决策者 / PM / 技术选型决策者

## Background

### 关键发现

6 个 provider 本质上分属两个层次，当前测试体系未反映这一区别：

**底层钱包基础设施 (Infrastructure)**：
- BNB Chain MCP — MCP server，本地密钥，原始转账 + 合约交互
- Crossmint Smart Wallets — Fireblocks 托管，REST API，签名 + 交易
- Privy Server Wallets — TEE 钱包，REST API，签名 + 交易 + 策略引擎

**应用层 Agent 工具包 (App Toolkit)**：
- Coinbase AgentKit — CDP 钱包 + 内置 swap/trade/faucet actions
- Minara AI — 托管 DeFi 助手，内置 swap/perps/deposit/Hyperliquid
- MoonPay Agents — 非托管，54 工具含 swap/bridge/预测市场

### 问题

1. 现有 16 个测试全部聚焦基础设施能力（密钥/签名/交易），缺失用户关心的应用层功能（Swap/DeFi/Bridge/预测市场/永续合约）
2. 需求筛选器使用开发者术语（"密钥生成"、"EIP-712 签名"），PM 看不懂
3. 如果直接加应用层测试，基础设施 provider 会全部 skip，评分被不公平拉低

### Oracle 建议

- 保留 `t01-t18` 平铺 ID，引入 `test_category` 元数据分组
- 区分 `skip`（有能力但未测）和 `not_applicable`（该层不适用），N/A 不进评分分母
- 筛选器改为两层结构（基础能力 | 应用能力）+ PM 视角功能 pills
- 加 `provider_type`（infra / app_toolkit）到 provider_meta

## 核心目标

1. **新增应用层测试维度** — Swap、DeFi、Bridge、预测市场、永续合约
2. **公平评分** — N/A 不入分母，基础设施 provider 不因应用层测试被惩罚
3. **PM 友好筛选器** — 从用户需求视角重新组织筛选项
4. **可视化区分** — N/A 用灰色渲染，与 FAIL 红色明确区分

## Phase 1: 数据模型扩展

### AC-006-1: 新增 test_category 常量映射
在 `app.js` 中新增 `TEST_CATEGORY` 常量，将每个测试归类：

```javascript
const TEST_CATEGORY = {
    // 基础能力 (infra)
    key_generate: 'infra',
    sign_message: 'infra',
    sign_typed_data: 'infra',
    send_tx: 'infra',
    multi_chain: 'infra',
    policy_enforcement: 'infra',
    session_delegation: 'infra',
    concurrent_ops: 'infra',
    failure_recovery: 'infra',
    preflight_fee: 'infra',
    rate_limit_resilience: 'infra',
    portability_recovery: 'infra',
    authorization_audit_trace: 'infra',
    // 架构特定 (arch-specific, 属于 infra 子类)
    derivation_path: 'infra',
    keychain_lock: 'infra',
    backup_recovery: 'infra',
    // 应用能力 (app)
    token_swap: 'app',
    defi_interaction: 'app',
    cross_chain_bridge: 'app',
    prediction_market: 'app',
    perps_trading: 'app',
};
```

### AC-006-2: 新增 provider_type 字段
在 `public_results.json` 每个 provider 的 `provider_meta` 中新增：
```json
"provider_type": "infra"   // 或 "app_toolkit"
```

分配规则：
- `infra`: bnbchain_mcp, crossmint, privy
- `app_toolkit`: coinbase_agentkit, minara, moonpay

### AC-006-3: 新增 5 个应用层测试数据
在 `public_results.json` 中为每个 provider 添加 t14-t18 测试结果：

| test_id | test_name | 说明 |
|---|---|---|
| t14 | token_swap | 代币兑换 — 能否通过内置工具完成 Token Swap |
| t15 | defi_interaction | DeFi 操作 — 能否与 DeFi 协议交互（质押/借贷/流动性） |
| t16 | cross_chain_bridge | 跨链桥接 — 能否将资产桥接到其他链 |
| t17 | prediction_market | 预测市场 — 能否在预测市场下注/交易 |
| t18 | perps_trading | 永续合约 — 能否在 Hyperliquid 等平台交易永续合约 |

各 provider 预期结果：

| Provider | t14 swap | t15 defi | t16 bridge | t17 prediction | t18 perps |
|---|---|---|---|---|---|
| BNB Chain MCP | not_applicable | not_applicable | not_applicable | not_applicable | not_applicable |
| Coinbase AgentKit | pass | skip | skip | skip | skip |
| Crossmint | not_applicable | not_applicable | not_applicable | not_applicable | not_applicable |
| Minara AI | pass | pass | skip | skip | pass |
| MoonPay Agents | pass | skip | pass | pass | skip |
| Privy | not_applicable | not_applicable | not_applicable | not_applicable | not_applicable |

**status 语义区分**：
- `pass` — 测试通过
- `fail` / `error` — 测试失败
- `skip` — 有能力执行但当前未测（如 provider 声称支持但本轮未验证）
- `not_applicable` — 该能力不在 provider 的产品定位范围内（infra provider 的应用层测试）

**status + 字段约束**：
| status | skip_reason | error_message | 含义 |
|---|---|---|---|
| pass | null | null | 测试通过 |
| fail | null | required | 测试失败 |
| error | null | required | 运行时错误 |
| skip | optional (e.g. `env_missing`, `not_verified`) | null | 有能力但当前未测 |
| not_applicable | required (`category_mismatch` / `architecture_mismatch`) | null | 不在产品定位范围 |

**注意**：`skip` 和 `not_applicable` 严禁互用。`skip` = 该 provider 类型下本应能测但本轮没跑；`not_applicable` = 结构性不匹配。

### AC-006-4: 更新 JS 常量映射
更新 `TEST_NAME_ZH`、`TEST_DESCRIPTIONS`、`CAP_TO_TEST`、`CAP_NAME_ZH`：

```javascript
// TEST_NAME_ZH 新增
token_swap: "代币兑换",
defi_interaction: "DeFi 操作",
cross_chain_bridge: "跨链桥接",
prediction_market: "预测市场",
perps_trading: "永续合约",

// TEST_DESCRIPTIONS 新增
token_swap: "验证能否通过内置工具完成 Token A→B 兑换（如 ETH→USDC）",
defi_interaction: "验证能否与 DeFi 协议交互（质押、借贷、流动性提供等）",
cross_chain_bridge: "验证能否将资产从链 A 桥接到链 B",
prediction_market: "验证能否在预测市场（如 Polymarket）下注或交易",
perps_trading: "验证能否在永续合约平台（如 Hyperliquid）开仓/平仓",

// CAP_TO_TEST 新增
token_swap: 'token_swap',
defi_ops: 'defi_interaction',
bridge: 'cross_chain_bridge',
prediction: 'prediction_market',
perps: 'perps_trading',

// CAP_NAME_ZH 新增
token_swap: '代币兑换',
defi_ops: 'DeFi 操作',
bridge: '跨链桥接',
prediction: '预测市场',
perps: '永续合约',
```

## Phase 2: 评分逻辑修正

### AC-006-5: N/A 不入评分分母
修改评分计算逻辑，`not_applicable` 测试从分母中剔除：

- **能力广度** = pass 数 / applicable 测试总数 × 100（排除 not_applicable）
- **可靠性** = pass 数 / 实际执行数 × 100（排除 not_applicable 和 skip）
- **覆盖度** = 实际执行数 / applicable 测试总数 × 100（排除 not_applicable）

影响函数：`computeRadarScores()` 中的分子/分母计算

### AC-006-6: 评分卡标注口径
在详情页评分卡（Score Card）中标注评分口径：
- 显示 "基于 X/Y 适用测试"（如 "基于 13/16 适用测试"）
- X = applicable 且实际运行的测试数，Y = applicable 测试总数
- 字号 0.75rem，颜色 `--text-tertiary`

## Phase 3: 筛选器 UX 重构

### AC-006-7: 两层筛选结构
将需求筛选器改为两层：

**第一层：类别 Tab**
```
全部 | 基础能力 (13) | 应用能力 (5)
```
- 点击类别 Tab 过滤下方功能 pills 的可见范围
- 数字为该类别的测试数量
- 默认选中 "全部"

**第二层：PM 视角功能 Pills**
按用户需求语言重新命名，分类展示：

基础能力：
- 创建钱包 (key_generate)
- 消息签名 (sign_message)
- 结构化签名 (sign_typed_data)
- 转账/交易 (send_tx)
- 多链支持 (multi_chain)
- 风控规则 (policy_enforcement)
- 临时授权 (session_delegation)
- 并发处理 (concurrent_ops)
- 故障恢复 (failure_recovery)
- Gas 预估 (preflight_fee)
- 限流韧性 (rate_limit_resilience)
- 钱包迁移 (portability_recovery)
- 审计追踪 (authorization_audit_trace)

应用能力：
- 代币兑换 Swap (token_swap)
- DeFi 操作 (defi_interaction)
- 跨链桥接 (cross_chain_bridge)
- 预测市场 (prediction_market)
- 永续合约 (perps_trading)

### AC-006-8: 筛选器标签更新
更新 `TEST_NAME_ZH` 中现有测试的中文名为 PM 友好措辞：

| 原名 | 新名 | 理由 |
|---|---|---|
| 密钥生成 | 创建钱包 | PM 理解"创建钱包"而非"密钥生成" |
| 消息签名 | 消息签名（登录验证） | 补充应用场景 |
| EIP-712 签名 | 结构化签名（Permit/订单） | 补充应用场景 |
| 发送交易 | 转账/交易 | 更直观 |
| 策略执行 | 风控规则 | PM 理解"风控" |
| 会话委托 | 临时授权 | 更直观 |
| 可移植恢复 | 钱包迁移 | 更直观 |

## Phase 4: 渲染层适配

### AC-006-9: 矩阵表 N/A 渲染
功能矩阵表中 `not_applicable` 状态渲染为：
- 灰色 "N/A" 文字（颜色 `--text-tertiary`）
- 不使用 ❌ 或 ⚠️ 图标
- 与 PASS ✅ / FAIL ❌ / SKIP ⚠️ 视觉上明确区分
- 矩阵表增加分组行标题："基础能力" 和 "应用能力"，作为视觉分隔

### AC-006-10: 详情页测试表 N/A 渲染
详情页测试结果表中 `not_applicable` 渲染为：
- 灰色 "N/A" 标签
- Filter pills 增加 "不适用 (N)" 按钮
- 默认排序中 not_applicable 排在 pass 之后（最低优先级）

### AC-006-11: Summary Table Provider 类型标识
在 summary table 的服务商名称旁增加 provider 类型标签：
- `infra` → 小标签 "基础设施"（灰底）
- `app_toolkit` → 小标签 "应用工具包"（黄底）
- 字号 0.65rem，pill 样式

### AC-006-12: 雷达图适配
雷达图 "能力广度" 和 "覆盖度" 维度使用 applicable-only 口径重新计算，与 AC-006-5 一致。

## Phase 5: 架构特定测试适配（tc 系列）— ❗ 前置到 Phase 1 之前执行

### AC-006-13: 架构特定测试 N/A 规则（❗ 必须在 AC-006-5 评分改动之前完成）
现有 tc01-tc03（derivation_path, keychain_lock, backup_recovery）数据当前对所有 provider 都是 `pass`，但非 Local 类 provider 不应该是 pass，应为 `not_applicable`。

**数据修正**：
| Provider | tc01 derivation_path | tc02 keychain_lock | tc03 backup_recovery |
|---|---|---|---|
| BNB Chain MCP (local) | pass | pass | pass |
| MoonPay Agents (local) | pass | pass | pass |
| Coinbase AgentKit (tee) | not_applicable | not_applicable | not_applicable |
| Crossmint (intent) | not_applicable | not_applicable | not_applicable |
| Privy (tee) | not_applicable | not_applicable | not_applicable |
| Minara AI (mpc_aa) | not_applicable | not_applicable | not_applicable |

Applicability 由 `meta.class` 决定（仅 `local` 适用），非 `provider_type`。

**实施顺序**：此 AC 必须在 Phase 2 评分改动之前落地，否则中间状态会产生错误评分。

## Phase 6: 级联组件适配（Oracle R1 补充）

### AC-006-14: Decision Bar + 失败摘要 N/A 排除
`renderDecisionBar()` 的 pass rate 计算和 blocker 逻辑必须排除 `not_applicable`：
- pass rate = pass 数 / applicable 测试数（排除 not_applicable）
- blocker 取第一个 fail/error，not_applicable 不算 blocker
- 阈值判定（推荐/谨慎/不推荐）基于 applicable-only pass rate

详情页 **fail summary**（“⚠️ N 项失败”）同样排除 not_applicable，仅统计真实 fail/error。

### AC-006-15: 能力清单 N/A 处理
详情页“能力清单”（基本信息 tab）中，通过 `CAP_TO_TEST` 映射的能力 tag：
- 如果对应测试结果为 `not_applicable`，tag 显示为灰色“不适用”（border-color: `--text-tertiary`）
- 不显示为红色失败或黄色跳过
- tooltip 显示“该能力不在此服务商产品定位范围内”

### AC-006-16: runner.py N/A 输出支持
runner.py 需要支持输出 `not_applicable` 状态：
- 在执行 adapter 前，根据 `provider_type` 和 `test_category` 判断适用性
- infra provider 的 app 测试自动输出 `{"status": "not_applicable", "skip_reason": "category_mismatch"}`
- 非 Local 类 provider 的 tc01-tc03 自动输出 `{"status": "not_applicable", "skip_reason": "architecture_mismatch"}`
- 无需创建 adapter 实例或调用任何 API

### AC-006-17: 共享 applicable 测试 selector 函数
新增一个共享工具函数 `getApplicableResults(provider)`，在以下所有消费方统一使用：
- `computeRadarScores()` — 雷达图 5 维度
- `renderDecisionBar()` — 结论条
- `renderScoreCard()` — 评分卡
- detail 页 fail summary — 失败摘要
- detail 页 filter pills — 状态统计

函数逻辑：`provider.results.filter(r => r.status !== 'not_applicable')`
避免各处重复实现过滤逻辑导致漂移。

## EXIT Gate

- [ ] 5 个新测试（t14-t18）数据已添加到 public_results.json
- [ ] provider_type 字段已添加到所有 6 个 provider
- [ ] tc01-tc03 非 Local provider 数据已修正为 not_applicable
- [ ] not_applicable 与 skip 在数据和渲染中明确区分
- [ ] 评分计算排除 not_applicable（N/A 不入分母）
- [ ] 评分卡标注 “基于 X/Y 适用测试”
- [ ] Decision Bar pass rate 排除 N/A
- [ ] 失败摘要排除 N/A
- [ ] 需求筛选器为两层结构（类别 Tab + PM 功能 Pills）
- [ ] 矩阵表和详情页 N/A 渲染为灰色，与 FAIL 红色区分
- [ ] 矩阵表有 “基础能力” / “应用能力” 分组行标题
- [ ] Summary table 显示 provider 类型标签
- [ ] 能力清单 tag N/A 渲染为灰色“不适用”
- [ ] 雷达图使用 applicable-only 口径
- [ ] 共享 getApplicableResults() 函数统一使用
- [ ] runner.py 支持输出 not_applicable 状态
- [ ] 0 JS error，所有 6 个 provider 正常渲染
- [ ] 375px / 768px / 1440px 无溢出

## Execution Log

| 日期 | 事件 | 详情 |
|------|------|------|
| 2026-03-05 | 发现 | 分析 provider 能力矩阵时发现 infra vs app 分层是关键区别 |
| 2026-03-05 | Oracle R1 | Oracle 建议保留平铺 ID + 元数据分层 + N/A 不入分母 + 两层筛选器 |
| 2026-03-05 | Issue 创建 | 5 Phase + 13 AC + EXIT Gate |
| 2026-03-05 | Oracle R2 完整性审查 | 发现 5 个缺失 AC（Decision Bar/fail summary/能力清单/runner/共享 selector）、实施顺序风险（AC-013 应前置）、Coinbase t15 修正为 skip |
| 2026-03-05 | Issue 更新 | 6 Phase + 17 AC + EXIT Gate，合入 Oracle R2 全部反馈 |
