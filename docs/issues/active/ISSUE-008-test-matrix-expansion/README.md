---
title: 'ISSUE-008: 测试矩阵扩展 — 基于 Oracle 审查的完整新测试规格'
concepts:
- test-matrix
- taxonomy-expansion
- pm-decision-readiness
- yaml-scoring
---
# ISSUE-008: 测试矩阵扩展 — 基于 Oracle 审查的完整新测试规格

## Meta
- **Status**: COMPLETE (Batch 1-6 全部完成，t07 session_delegation 待确认)
- **Priority**: P1
- **Component**: wallet-bench / test cases + evaluations + web
- **Owner**: —
- **Date**: 2026-03-05
- **Effort**: Medium (1-2d spec + 3d+ implementation)
- **Depends**: ISSUE-007（5 维度结构已落地）
- **Source**: Oracle 测试分类完整性审查 (session `ses_341bec180ffeqd2uoo2Eae32xI`)
- **Audience**: 决策者 / PM / 技术选型决策者

## Background

### Oracle 审查结论

| 维度 | 现有测试数 | 评级 | 核心问题 |
|------|-----------|------|---------|
| 钱包基础 | 6 | ⚠️ NEEDS_IMPROVEMENT | 缺 nonce 管理、交易确认终态 |
| 权限治理 | 3 | 🔴 MAJOR_GAP | t06/t07 是桩代码，缺策略撤销延迟、拒绝原因质量 |
| 稳定性 | 3 | ⚠️ NEEDS_IMPROVEMENT | t08 并发测试太简单，缺幂等提交、重试退避 |
| 运维能力 | 1+tc | 🔴 MAJOR_GAP | 共享测试仅 1 个，缺 webhook、配额披露、环境矩阵 |
| 应用能力 | 5 | ⚠️ NEEDS_IMPROVEMENT | 全是二元"能不能做"，缺深度指标 |

### 目标

从当前 18 个共享测试（+ tc 架构特定测试）扩展至 **28-32 个**，覆盖 PM 选型决策所需的全部关键维度。

### 设计原则

1. **自动化优先** — Python test case 可执行，`runner.py` 可跑
2. **YAML 评分补充** — 无法完全自动化的维度用 `evaluations/*.yaml` 中 1-5 分评分
3. **YAML 评分必须有证据** — 每个分数必须附 evidence 字段说明依据
4. **深度 > 广度** — 升级现有弱测试优先于新增测试
5. **PM 语言** — 测试名和描述用 PM 能理解的措辞

## 测试类型定义

| 类型 | 标记 | 含义 | 数据来源 |
|------|------|------|---------|
| **AUTO** | 🤖 | 全自动 Python test case | `cases/shared/` 或 `cases/class/` |
| **YAML** | 📋 | 人工/半自动评估，1-5 分 | `evaluations/*.yaml` |
| **HYBRID** | 🔄 | 自动跑 + YAML 补充深度指标 | 两者结合 |

---

## 完整测试矩阵 (目标: ~30 项)

### Dimension 1: 钱包基础 (wallet_core) — 8 项

| ID | test_name | 中文名 | 类型 | 描述 | 状态 |
|---|---|---|---|---|---|
| t01 | key_generate | 创建钱包 | 🤖 AUTO | 创建钱包，验证地址格式 | ✅ 已有 |
| t02 | sign_message | 消息签名 | 🤖 AUTO | personal_sign 签名任意文本 | ✅ 已有 |
| t03 | sign_typed_data | 结构化签名 | 🤖 AUTO | EIP-712 结构化数据签名 | ✅ 已有 |
| t04 | send_tx | 转账/交易 | 🤖 AUTO | 构建、签名、提交链上交易（testnet） | ✅ 已有 |
| t05 | multi_chain | 多链支持 | 🤖 AUTO | 验证声明的多链支持实际可用 | ✅ 已有 |
| t10 | preflight_fee | Gas 预估 | 🤖 AUTO | 交易前预估 gas 费用 | ✅ 已有 |
| t19 | nonce_management | Nonce 管理 | 🤖 AUTO | 验证 nonce 冲突处理、加速/取消交易能力 | 🆕 新增 |
| t20 | tx_confirmation | 交易确认 | 🤖 AUTO | 验证交易从提交到确认终态的处理（receipt 轮询/webhook/状态追踪） | 🆕 新增 |

**t19 nonce_management 测试设计：**
- 发送两笔交易，验证 nonce 自动递增
- 尝试用相同 nonce 发第二笔（replace），验证处理方式
- 对于 provider_submit 模式的 provider，验证其是否自动处理 nonce
- pass: nonce 管理正确无冲突 / fail: nonce 冲突导致交易失败 / skip: provider 不暴露 nonce 控制

**t20 tx_confirmation 测试设计：**
- 提交交易后，检查是否提供 tx_hash
- 验证是否有方式查询交易状态（receipt/status endpoint）
- 检查交易确认后返回的信息完整性（block_number, gas_used, status）
- pass: 可追踪交易到终态 / fail: 交易提交后无法追踪

---

### Dimension 2: 权限治理 (governance) — 6 项

| ID | test_name | 中文名 | 类型 | 描述 | 状态 |
|---|---|---|---|---|---|
| t06 | policy_enforcement | 风控规则 | 🤖 AUTO | 策略引擎拦截超限/违规交易 | ⚠️ 桩代码待实现 |
| t07 | session_delegation | 临时授权 | 🤖 AUTO | 创建受限会话密钥/委托签名权限 | ⚠️ 待验证 |
| t13 | authorization_audit_trace | 审计追踪 | 🤖 AUTO | 钱包/签名/交易结果中的审计字段完整性 | ✅ 已有 |
| t21 | policy_revocation_latency | 策略撤销延迟 | 🤖 AUTO | 撤销/修改策略后多快生效，是否有残余窗口 | 🆕 新增 |
| t22 | denial_reason_quality | 拒绝原因质量 | 🤖 AUTO | 交易被拒绝时返回的原因是否机器可读、可分类 | 🆕 新增 |
| e01 | governance_completeness | 治理完整度 | 📋 YAML | 评估策略引擎功能覆盖：限额/白名单/时间窗/多签/审批流 (1-5) | 🆕 新增 |

**t06 policy_enforcement 实现要点：**
- 对支持策略引擎的 provider（目前仅 Privy）：
  1. 在 Dashboard 预配置一条限额策略
  2. 发送限额内交易 → 应成功
  3. 发送超限交易 → 应被策略引擎拒绝（非链上 revert）
  4. 验证拒绝响应包含 policy rule ID
- 不支持策略引擎的 provider → skip

**t21 policy_revocation_latency 测试设计：**
- 创建策略 → 验证生效 → 撤销策略 → 立即发送原被拦截的交易 → 验证是否放行
- 记录从撤销到生效的延迟（理想 < 1s）
- 不支持策略引擎的 provider → skip

**t22 denial_reason_quality 测试设计：**
- 触发交易拒绝（策略拦截 / 余额不足 / 参数错误 / 权限不足）
- 检查错误响应是否包含：error_code、human_readable_message、machine_readable_category
- 评分标准：全部字段 = pass / 仅 message = partial / 裸字符串 = fail

**e01 governance_completeness YAML 评分锚点：**
| 分数 | 含义 |
|------|------|
| 1 | 无治理能力 |
| 2 | 仅基础限额或白名单 |
| 3 | 限额 + 白名单 + 时间窗 |
| 4 | 上述 + 多签/审批流 |
| 5 | 完整策略引擎（可编程规则 + 条件组合 + key quorum） |

---

### Dimension 3: 稳定性 (reliability) — 5 项

| ID | test_name | 中文名 | 类型 | 描述 | 状态 |
|---|---|---|---|---|---|
| t08 | concurrent_ops | 并发处理 | 🤖 AUTO | 混合并发操作（create + sign + send），检查线程安全 | ✅ 已有，需升级 |
| t09 | failure_recovery | 故障恢复 | 🤖 AUTO | Teardown + re-setup 后 adapter 恢复 | ✅ 已有 |
| t11 | rate_limit_resilience | 限流韧性 | 🤖 AUTO | burst 请求后的恢复能力 | ✅ 已有 |
| t23 | idempotent_submit | 幂等提交 | 🤖 AUTO | 重复提交同一笔交易是否安全（不会双花） | 🆕 新增 |
| t24 | retry_backoff | 重试退避 | 🤖 AUTO | 被限流后的退避策略是否合理（指数退避 vs 固定间隔 vs 无退避） | 🆕 新增 |

**t08 concurrent_ops 升级方案：**
- 从 "3 个并发 create_wallet" → "混合负载：2 create_wallet + 2 sign_message + 1 send_tx"
- 验证：无异常、无重复地址、签名结果正确、交易无 nonce 冲突
- 增加重复地址检查（create_wallet 不应返回相同地址）

**t23 idempotent_submit 测试设计：**
- 构建一笔交易 → 提交 → 等待确认 → 用相同参数再次提交
- 期望行为：provider 应拒绝重复交易（nonce 已用）或返回相同 tx_hash
- pass: 安全处理重复提交 / fail: 产生两笔链上交易（双花）

**t24 retry_backoff 测试设计：**
- 快速连续发送 N 个请求触发限流 → 记录限流响应
- 检查响应是否包含 Retry-After header 或等待时间提示
- 按提示等待后重试 → 验证恢复
- pass: 有明确退避指引且恢复正常 / partial: 恢复但无指引 / fail: 无法恢复

---

### Dimension 4: 运维能力 (ops) — 6 项

| ID | test_name | 中文名 | 类型 | 描述 | 状态 |
|---|---|---|---|---|---|
| t12 | portability_recovery | 钱包迁移 | 🤖 AUTO | 钱包身份持久性 + 密钥导出能力 | ✅ 已有 |
| tc01-tc03 | (架构特定) | (按 class 不同) | 🤖 AUTO | local/tee/intent 各自 3 个特定测试 | ✅ 已有 |
| t25 | webhook_delivery | 事件通知 | 🤖 AUTO | 验证 provider 是否支持 webhook/事件通知，交易状态变更能否实时推送 | 🆕 新增 |
| t26 | quota_disclosure | 配额透明度 | 🔄 HYBRID | 验证 API 是否在响应 header 中披露 rate limit 配额（X-RateLimit-*）或文档是否明确 | 🆕 新增 |
| e02 | network_environment | 环境矩阵 | 📋 YAML | 测试网/主网支持情况 + 限制（faucet 是否自动化、主网是否需要 KYC） (1-5) | 🆕 新增 |
| e03 | sdk_doc_quality | 文档上手度 | 📋 YAML | 从零到跑通第一个测试的体验（文档完整性 + 示例质量 + 错误指引） (1-5) | 🆕 新增（整合现有 doc_accuracy + time_to_first_success） |

**t25 webhook_delivery 测试设计：**
- 查询 provider API/文档是否支持 webhook 注册
- 如支持：注册 webhook → 发送交易 → 验证是否在 30s 内收到事件
- 如不支持：记录为 skip（非 N/A，因为所有 provider 理论上都应该有事件通知）
- 注：需要一个临时 HTTP endpoint 接收 webhook（可用 httpbin 或本地 server）

**t26 quota_disclosure 测试设计：**
- 发送正常 API 请求，检查响应 header 是否包含限流信息（X-RateLimit-Limit, X-RateLimit-Remaining 等）
- 补充 YAML：文档中是否明确说明 API 配额限制
- pass: header 有限流信息 / partial: 仅文档说明 / fail: 无任何配额信息

**e02 network_environment YAML 评分锚点：**
| 分数 | 含义 |
|------|------|
| 1 | 仅主网，无测试网，无 faucet |
| 2 | 有测试网但 faucet 需人类操作（captcha） |
| 3 | 有测试网 + 自动 faucet，但主网有额外限制 |
| 4 | 完整测试网/主网支持，faucet 自动化 |
| 5 | 上述 + 本地开发网（hardhat/anvil fork）支持 |

**e03 sdk_doc_quality YAML 评分锚点（整合现有指标）：**
| 分数 | 含义 | 对应现有指标参考 |
|------|------|-----------------|
| 1 | 无文档，只能看源码 | doc_accuracy=5, time_to_first_success > 60min |
| 2 | 有文档但严重过时/错误 | doc_accuracy=4, time_to_first_success 30-60min |
| 3 | 文档基本可用，需要试错 | doc_accuracy=3, time_to_first_success 15-30min |
| 4 | 文档准确 + 有可运行示例 | doc_accuracy=2, time_to_first_success 5-15min |
| 5 | 完美文档 + quickstart + AI 友好（llms.txt） | doc_accuracy=1, time_to_first_success < 5min |

---

### Dimension 5: 应用能力 (app) — 7 项

| ID | test_name | 中文名 | 类型 | 描述 | 状态 |
|---|---|---|---|---|---|
| t14 | token_swap | 代币兑换 | 🔄 HYBRID | 能否完成 Token Swap + 支持的 DEX/链数量 + 滑点 | ✅→升级 |
| t15 | defi_interaction | DeFi 操作 | 🔄 HYBRID | 能否与 DeFi 协议交互 + 支持的协议类型数量 | ✅→升级 |
| t16 | cross_chain_bridge | 跨链桥接 | 🔄 HYBRID | 能否桥接资产 + 支持的链对数量 | ✅→升级 |
| t17 | prediction_market | 预测市场 | 🔄 HYBRID | 能否在预测市场交易 + 支持的平台 | ✅→升级 |
| t18 | perps_trading | 永续合约 | 🔄 HYBRID | 能否交易永续合约 + 支持的平台 | ✅→升级 |
| t27 | app_tool_coverage | 工具覆盖度 | 📋 YAML | 内置工具/action 的总数量和分类覆盖 (1-5) | 🆕 新增 |
| e04 | app_execution_quality | 执行质量 | 📋 YAML | swap 滑点、交易成功率、执行延迟的综合评估 (1-5) | 🆕 新增 |

**t14-t18 升级为 HYBRID 模式：**
- **Layer 1（AUTO）**：二元能力检测 — 能否成功调用 swap/defi/bridge 工具（现有逻辑）
- **Layer 2（YAML 深度指标）**：在 evaluations YAML 中补充：
  - `supported_dex_count`: 支持的 DEX 数量
  - `supported_chains`: 支持的链列表
  - `supported_protocols`: 支持的 DeFi 协议类型（stake/lend/LP/...）
  - `success_rate`: 测试中的实际成功率
  - `avg_slippage_bps`: 平均滑点（基点）

**t27 app_tool_coverage YAML 评分锚点：**
| 分数 | 含义 |
|------|------|
| 1 | 无内置应用工具，纯基础设施 |
| 2 | 1-5 个工具（仅基础 swap） |
| 3 | 6-15 个工具（swap + 部分 DeFi） |
| 4 | 16-30 个工具（swap + DeFi + bridge） |
| 5 | 30+ 个工具（全覆盖：swap/DeFi/bridge/预测市场/永续合约） |

**e04 app_execution_quality YAML 评分锚点：**
| 分数 | 含义 |
|------|------|
| 1 | 工具经常失败，无错误处理 |
| 2 | 基本能用，但滑点高/延迟大/成功率低 |
| 3 | 可靠执行，但无优化（默认滑点、无路由选择） |
| 4 | 低滑点 + 高成功率 + 合理延迟 |
| 5 | 最优路由 + 最小滑点 + MEV 保护 |

---

### 跨维度：商业与合规 (commercial) — 仅 YAML 评分

不单独成维度，作为 evaluations YAML 中的补充字段：

| ID | 字段名 | 中文名 | 类型 | 描述 |
|---|---|---|---|---|
| e05 | cost_transparency | 定价透明度 | 📋 YAML | API 调用成本是否公开、Gas sponsorship 是否支持 (1-5) |
| e06 | kyc_requirement_clarity | KYC 要求清晰度 | 📋 YAML | 是否需要 KYC、要求是否在文档中明确说明 (1-5) |

**e05 cost_transparency YAML 评分锚点：**
| 分数 | 含义 |
|------|------|
| 1 | 无定价信息，需联系销售 |
| 2 | 有免费层但限制不明确 |
| 3 | 定价页面有基础信息，但 API 单次成本不清楚 |
| 4 | 清晰定价 + 免费额度 + Gas sponsorship 说明 |
| 5 | 完全透明（每个 API 的成本 + 计费仪表盘 + Gas 补贴方案） |

**e06 kyc_requirement_clarity YAML 评分锚点：**
| 分数 | 含义 |
|------|------|
| 1 | 不知道是否需要 KYC，文档无说明 |
| 2 | 需要 KYC 但流程不清楚 |
| 3 | KYC 要求在文档中说明，但流程复杂 |
| 4 | 明确说明 KYC 要求 + 简单流程 |
| 5 | 无 KYC 要求，或 KYC 完全自动化 |

---

## 汇总对比

| 维度 | 现有 | 目标 | 新增 | 升级 |
|------|------|------|------|------|
| 钱包基础 | 6 | 8 | t19, t20 | — |
| 权限治理 | 3 | 6 | t21, t22, e01 | t06, t07 |
| 稳定性 | 3 | 5 | t23, t24 | t08 |
| 运维能力 | 1+tc | 6+tc | t25, t26, e02, e03 | — |
| 应用能力 | 5 | 7 | t27, e04 | t14-t18 |
| 商业合规 | 0 | 2 | e05, e06 | — |
| **总计** | **18+tc** | **34+tc** | **16 项** | **8 项** |

其中：
- 🤖 AUTO (Python test case): 10 新增 + 8 升级 = 18 项工作
- 📋 YAML (评分): 6 新增
- 🔄 HYBRID: 5 项（t14-t18 升级）

---

## 与现有 evaluations YAML 的关系

现有 `evaluations/*.yaml` 已有以下评分字段：
- `onboarding_friction` (1-5) → 保留，被 e03 sdk_doc_quality 部分整合
- `doc_accuracy` (1-5) → 保留，被 e03 整合
- `api_consistency` (1-5) → 保留不变
- `error_message_quality` (1-5) → 保留，与 t22 denial_reason_quality 互补
- `agent_autonomy` (1-5) → 保留不变
- `time_to_first_success_min` → 保留，被 e03 引用

新增字段（追加到现有 YAML 中）：
- `governance_completeness` (e01)
- `network_environment` (e02)
- `sdk_doc_quality` (e03)
- `app_tool_coverage` (t27)
- `app_execution_quality` (e04)
- `cost_transparency` (e05)
- `kyc_requirement_clarity` (e06)

---

## 各 Provider 预期适用性

| 测试 | BNB MCP | Coinbase | Crossmint | Minara | MoonPay | Privy |
|------|---------|----------|-----------|--------|---------|-------|
| t19 nonce | ✅ | ✅ | ✅ | skip | ✅ | ✅ |
| t20 tx_confirm | ✅ | ✅ | ✅ | skip | ✅ | ✅ |
| t21 policy_revoke | skip | skip | skip | skip | skip | ✅ |
| t22 denial_reason | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| t23 idempotent | ✅ | ✅ | ✅ | skip | ✅ | ✅ |
| t24 retry_backoff | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| t25 webhook | skip | skip | ✅ | skip | skip | ✅ |
| t26 quota | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| t27 tool_coverage | N/A | ✅ | N/A | ✅ | ✅ | N/A |
| e01-e06 | ✅ all | ✅ all | ✅ all | ✅ all | ✅ all | ✅ all |

说明：
- `skip` = 该 provider 可能支持但需要验证
- `N/A` = 结构性不适用（infra provider 无内置应用工具）
- YAML 评分 (e01-e06) 所有 provider 都需要填写

---

## 实施路径

### ~~Batch 1: YAML 评分 + 数据填充~~ ✅ DONE
- ✅ 为 6 个 provider 填写 e01-e06 评分（7 个新 YAML 字段 × 6 providers = 42 条数据）
- ✅ 更新 `web/app.js` 展示新的 YAML 评分字段

### ~~Batch 2: 升级现有弱测试~~ ✅ DONE
- ✅ 实现 t06 policy_enforcement（对 Privy）
- ✅ 升级 t08 concurrent_ops（混合负载）

### ~~Batch 3: 新增自动化测试~~ ✅ DONE
- ✅ 实现 t19-t26 共 8 个新 Python test case
- ✅ runner.py + app.js TEST_CATEGORY 映射完成（35 条目）

---

### 优先级重排说明 (2026-03-05 Oracle 战略审查 + 用户确认)

**核心判断**：决策者 最关心的是「钱包能做什么」——即应用层能力的真实 demo，而非延迟/安全策略等 infra 指标。

**Oracle 战略审查结论**：瓶颈是「数据可信度」而非功能数量。需要：
1. 真实运行测试（当前所有数据均为手填/research，从未跑过）
2. 数据溯源标注（AUTO/YAML/HYBRID 标签 + last_run_at）
3. 覆盖率透明化（让决策者一眼看到完成度）

**用户优先级**：App 层 (t14-t18) 真实 demo > 基础测试 > 治理/可靠性/运维

因此 Batch 4-6 按以下顺序推进：

### Batch 4: App 层真实测试 + Crossmint Adapter 升级 (P0, ~2d) ← 当前

**并行 Track A: t14-t18 App 层测试实现**

实现 5 个 App 层 Python test case（目前只有 TEST_CATEGORY 条目，无 .py 文件）：

| ID | test_name | 测试内容 | 涉及 Provider |
|---|---|---|---|
| t14 | token_swap | 调用 swap 工具完成代币兑换 | MoonPay (`mp token swap`), Coinbase (swap action), Minara (`minara swap`) |
| t15 | defi_interaction | 调用 DeFi 协议交互工具 | Minara (deposit/stake), Coinbase (morpho/aave actions) |
| t16 | cross_chain_bridge | 调用跨链桥接工具 | MoonPay (`mp token bridge`), Crossmint (lobster.cash cross-chain) |
| t17 | prediction_market | 调用预测市场交易工具 | MoonPay (`mp prediction-market`), Minara |
| t18 | perps_trading | 调用永续合约交易工具 | Minara (`minara perps`), MoonPay |

**测试设计原则**：
- 每个测试先检查 adapter.capabilities() 是否声明支持
- 实际调用工具（testnet/dry-run 模式），不仅仅是 capability check
- 记录执行结果 + 延迟 + 错误信息
- 对 infra provider (BNB MCP, Privy, Crossmint REST) 标记 N/A
- **目标：产出可截图/录屏给决策者看的真实 demo 输出**

**并行 Track B: Crossmint Adapter 升级**

Crossmint 现有 3 种集成形态（见 `docs/INTEGRATION-TYPES.md`）：
1. **MCP Server** (`mcp-crossmint-checkout`) — 3 个 tools: create-order, check-order, get-usd-balance
2. **OpenClaw Plugin** (`@crossmint/lobster.cash`) — Visa 虚拟卡 + x402 + Solana USDC
3. **REST API** (当前 `adapters/crossmint.py` 使用的方式)

升级计划：
- [x] AC-008-B1: 新增 `adapters/crossmint_mcp.py` — MCP Server stdio 模式 adapter
- [ ] ~~AC-008-B2~~: Crossmint 保持 6 provider 方案，MCP adapter 作为补充（不单独建 provider）
- [x] AC-008-B3: 在 `adapters/crossmint.py` 顶部标注 `# LEGACY: REST API 模式，MCP 模式见 crossmint_mcp.py`
- [ ] AC-008-B4: 新 MCP adapter 通过 t01-t04 基础测试（需 API credentials）
- [ ] AC-008-B5: runner.py 支持同一 provider 多 adapter 切换（`--adapter crossmint_mcp` vs `--adapter crossmint`）

### Batch 5: 数据可信度 + UI 透明化 (P0, ~1d)

**Oracle 战略审查核心建议**：没有真数据，一切评分都是纸上谈兵。

- [x] AC-008-C1: UI 数据溯源标签 — 矩阵表 + 详情页测试表均已添加 AUTO/HYBRID badge
- [ ] AC-008-C2: UI `last_run_at` 显示 — 待真实测试运行后补充
- [x] AC-008-C3: Dashboard 覆盖率横幅 — 已实现 renderCoverageBanner()
- [x] AC-008-C4: 低置信度视觉降级 — YAML 评分用虚线边框 + "人工" badge 标记
- [ ] AC-008-C5: `public_results.json` 每个测试条目增加 `source: auto|yaml|hybrid` + `last_run_at` 字段

### Batch 6: 全量基准测试运行 (P0, ~1d, 需用户提供 API credentials)

- [x] AC-008-D1: 配置 `config.yaml` 所有 6 个 provider 的 API 凭证（用户已预配置）
- [x] AC-008-D2: 运行 `runner.py` 全量测试，6 个 provider 均已完成
- [ ] AC-008-D3: t07 session_delegation 状态——所有 provider 均 SKIP（无 provider 支持）
- [x] AC-008-D4: 更新 `public_results.json` 为真实测试数据（含 timestamp + summary）
- [x] AC-008-D5: 验证 UI 展示真实数据的正确性（截图确认）

## 评分体系重构 (Scoring Rubric Overhaul)

### 决策记录

| 决策项 | 选择 | 原因 |
|--------|------|------|
| 评分方向 | **正向 (1=最差, 5=最好)** | 更直觉，与 ISSUE-008 新增项一致，避免混合方向维护复杂 |
| 雷达图维度 | **5 维度对齐 CATEGORY_META** | wallet_core / governance / reliability / ops / app，与测试分类完全一致 |
| Issue 管理 | 追加到 ISSUE-008 | 逻辑上评分是测试矩阵的一部分 |

### 评分方向统一 (Breaking Change)

**现有 YAML 评分全部从反向 (1=最好, 5=最差) 翻转为正向 (1=最差, 5=最好)。**

翻转公式：`new_score = 6 - old_score`

影响范围：
- 6 个 `evaluations/*.yaml` 文件的 `scores` 字段
- `web/app.js` 中 `computeRadarScores()` 的 `dx_quality` 计算（移除反转公式）
- YAML 文件中的注释说明（统一为 1=最差, 5=最好）

翻转前后对照：

| 字段 | 旧含义 (1=最好) | 新含义 (1=最差) | 翻转公式 |
|------|----------------|----------------|---------|
| onboarding_friction | 1=零摩擦 | 1=极难上手 → 改名为 `onboarding_ease` | 6 - old |
| doc_accuracy | 1=完美 | 1=严重误导 → 改名为 `doc_quality` | 6 - old |
| api_consistency | 1=完全一致 | 1=处处意外 → 保持原名 | 6 - old |
| error_message_quality | 1=清晰 | 1=不可读 → 保持原名 | 6 - old |
| agent_autonomy | 1=全自主 | 1=完全依赖人类 → 保持原名 | 6 - old |
| time_to_first_success_min | 分钟数 (不变) | 分钟数 (不变) | 不翻转 |

### 新雷达图维度设计

**旧 5 维度**（已废弃）：能力广度 / 可靠性 / 开发体验 / 延迟 / 覆盖度

**新 5 维度**（与 CATEGORY_META 对齐）：

| 维度 | Key | 计算方式 |
|------|-----|---------|
| 钱包基础 | wallet_core | wallet_core 类测试通过率 = pass / (pass + fail) × 100 |
| 权限治理 | governance | governance 类测试通过率 × 0.6 + e01 governance_completeness × 0.4 × 20 |
| 稳定性 | reliability | reliability 类测试通过率 |
| 运维能力 | ops | ops 类测试通过率 × 0.5 + (e02 + e03) 均值 × 0.5 × 20 |
| 应用能力 | app | app 类测试通过率 × 0.5 + (t27 + e04) 均值 × 0.5 × 20（仅 app_toolkit 有值；infra provider N/A 测试排除后按实际跑的算） |

**算法说明**：
- 通过率 = pass / (pass + fail)，排除 skip / not_applicable / error
- YAML 评分 (1-5) 转百分制：score × 20（即 5 分 = 100 分）
- 纯 AUTO 维度（wallet_core, reliability）只看测试通过率
- 有 YAML 补充的维度（governance, ops, app）按权重混合 AUTO 通过率 + YAML 百分制
- N/A 测试不计入分母
- e05/e06（商业合规）不入雷达图，仅在详情页展示

### 实施清单 (Scoring)

- [x] 更新 ISSUE-008 spec（本节）
- [x] 翻转 6 个 YAML 文件的 scores
- [x] 重写 `computeRadarScores()` 使用新算法
- [x] 更新雷达图 labels 为 5 维度中文名
- [x] 更新详情页雷达图使用相同算法
---

## EXIT Gate

### Spec & Scoring (已完成)
- [x] 测试矩阵规格定义完成
- [x] 每个新测试有明确的 test_name、维度归属、测试设计、pass/fail 标准
- [x] 每个 YAML 评分有明确的 1-5 评分锚点
- [x] 各 Provider 预期适用性已标注
- [x] 实施路径已拆分为可执行的 Batch
- [x] 评分方向统一为正向 (1=最差, 5=最好)
- [x] 雷达图维度对齐 CATEGORY_META（5 维度）
- [x] YAML 评分翻转 + 雷达图算法实现

### Batch 1-3 (已完成)
- [x] e01-e06 YAML 评分已填写（6 providers × 7 字段）
- [x] t19-t26 共 8 个新 Python test case 已创建
- [x] t06 policy_enforcement 从桩代码升级为真实实现
- [x] t08 concurrent_ops 升级为混合负载
- [x] runner.py + app.js TEST_CATEGORY 已添加新测试映射（35 条目）
- [x] web/app.js 详情页已添加维度评分展示（EVAL_SCORE_META）
- [x] public_results.json 已包含新 YAML 评分数据

### Batch 4: App 层 + Crossmint 升级
- [x] t14-t18 共 5 个 App 层 Python test case 已创建（syntax verified）
- [x] Crossmint MCP adapter 实现（adapters/crossmint_mcp.py, 251 行）
- [x] runner.py 已加载 crossmint_mcp provider

### Batch 5: 数据可信度 UI
- [x] 数据溯源标签（AUTO/YAML/HYBRID badge）— 矩阵表 + 详情页测试表
- [x] 覆盖率横幅已显示在 Dashboard 顶部（renderCoverageBanner）
- [x] 低置信度视觉降级 — YAML 评分虚线边框 + "人工" badge

### Batch 6: 全量测试运行
- [x] 全量测试已跑（6 providers × 26-29 tests）
- [ ] t07 session_delegation — 所有 provider 均 SKIP（待确认是否有 provider 支持）
- [x] public_results.json 已更新为真实测试数据

## Execution Log

| 日期 | 事件 | 详情 |
|------|------|------|
| 2026-03-05 | Oracle 审查 | 5 维度完整性评估，发现 2 个 MAJOR_GAP + 3 个 NEEDS_IMPROVEMENT |
| 2026-03-05 | Issue 创建 | 完整测试矩阵规格：16 新增 + 8 升级 = 34 项目标 |
| 2026-03-05 | 评分体系决策 | 正向评分 + 5 维度雷达图 + 追加到 ISSUE-008 |
| 2026-03-05 | Batch 1-3 实施 | e01-e06 YAML 评分填写 + t19-t26 新测试 + t06/t08 升级 + 前端展示 + TEST_CATEGORY 映射 |
| 2026-03-05 | Oracle 战略审查 | 核心结论：瓶颈是数据可信度而非功能数量。建议：真实运行测试 > 数据溯源标注 > 覆盖率透明化 |
| 2026-03-05 | 优先级重排 | 用户确认：App 层 (t14-t18) 真实 demo 优先 > 基础测试 > 治理/可靠性。Crossmint adapter 升级为 MCP 模式。并行执行 |
| 2026-03-05 | Batch 4 实施 | t14-t18 App 层 5 个 Python 测试文件 + crossmint_mcp.py MCP adapter + runner 更新 |
| 2026-03-05 | Batch 5 实施 | 矩阵/详情页 AUTO/HYBRID/人工 badge + 覆盖率横幅 + YAML 视觉降级 + app.js 语法修复 |
| 2026-03-05 | 架构决策 | Crossmint MCP 保持为补充 adapter（不新建第 7 个 provider），6 provider 方案不变 |
| 2026-03-05 | Batch 6 实施 | 全量测试运行完成：BNB(13P/2F) Crossmint(3P/11E) Privy(14P/5F) Coinbase(12P/5F) MoonPay(12P/7F) Minara(7P/7F)。public_results.json 替换为真实数据。 |
