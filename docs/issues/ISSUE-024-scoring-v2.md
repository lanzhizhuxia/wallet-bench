# ISSUE-024 — 评分体系 v2：9 维雷达 + 双评分公式 + 维度权重重构

**Status**: OPEN  
**Priority**: P0  
**Created**: 2026-03-08  
**Depends on**: —  
**Blocks**: ISSUE-025, ISSUE-026

---

## 背景

当前评分体系（v1）采用 7 维等权雷达图，存在以下问题：

1. **应用场景被合成一个维度** — Polymarket Agent 只做预测市场，在"应用能力"维度被其他 4 个不支持的场景拖低分，不公平
2. **非应用维度占比过重** — 治理(12%) + 安全(4%) + 运维(29%) = 45%，而用户核心关注的应用层只占 10%
3. **等权模型不反映真实选型需求** — 用户是 Agent 开发者，需要跑链上策略（套利/薅羊毛/挖矿），应用层和 Agent 集成度才是决策核心
4. **缺少性能维度** — 套利场景对延迟极度敏感，当前无独立性能维度

## 目标

将评分体系从 v1（7 维等权）升级为 v2（9 维加权 + 双评分公式），使排名结果直接反映 "AI Agent 跑链上策略" 的选型需求。

---

## 一、新雷达图：9 个维度

### 5 个应用场景维度（独立计分，不合并）

| 维度 key | 中文 | 说明 |
|----------|------|------|
| `swap` | Swap 兑换 | Token 兑换、路由发现、滑点保护、MEV 防护、授权管理 |
| `defi_lending` | DeFi 借贷 | Aave 等借贷协议操作、多步组合流程 |
| `cross_chain` | 跨链 | 跨链桥接、套利双腿原子性、状态一致性 |
| `prediction_market` | 预测市场 | Polymarket 等预测市场操作 |
| `perps` | 永续合约 | Hyperliquid 等永续合约交易 |

### 4 个基础/加分维度

| 维度 key | 中文 | 说明 |
|----------|------|------|
| `agent_autonomy` | Agent 自主性 | 工具发现、零样本完成、错误自恢复、多步规划、上下文效率、Function Calling 兼容 |
| `performance` | 性能 | 交易延迟 p50/p95/p99、并发吞吐、冷启动、Gas 估算精度 |
| `wallet_basics` | 钱包基础 | 创建钱包、签名、转账、多链支持（前置条件/基线门槛） |
| `enterprise_readiness` | 企业就绪度 | 治理 + 安全 + 运维 合并为一个加分维度 |

---

## 二、双评分公式

### A. 场景适配分（FitScore）— 用户主视角

用户选择一个目标场景 j，按此公式排序：

```
FitScore_j = 0.55 × S_j + 0.20 × A + 0.15 × P + 0.10 × W
```

- `S_j` = 场景 j 的维度分（0-100）
- `A` = Agent 自主性分
- `P` = 性能分
- `W` = 钱包基础分
- Enterprise 不参与 FitScore

**效果**：Polymarket Agent 在"预测市场"场景下 FitScore 很高，即使其他场景为零。

### B. 平台综合分（PlatformScore）— 全局排行

用最强两个场景的均值，不惩罚专精型供应商：

```
AppTop2 = (最高场景分 + 第二高场景分) / 2

PlatformScore = 0.27 × A + 0.23 × P + 0.20 × W + 0.20 × AppTop2 + 0.10 × E
```

- `E` = 企业就绪度
- 如果只有 1 个场景：AppTop2 = 该场景分 / 2
- 如果 0 个场景：AppTop2 = 0

### C. 覆盖度徽章

```
Coverage = #(S_i >= 40) / 5
```

展示为 `Coverage: 2/5` 等，不进入分数计算。

---

## 三、测试项→维度映射（v2）

### 现有测试重新归类

| 原维度 | 测试 ID | 新维度 |
|--------|---------|--------|
| wallet_core | t01 key_generate | wallet_basics |
| wallet_core | t02 sign_message | wallet_basics |
| wallet_core | t03 sign_typed_data | wallet_basics |
| wallet_core | t04 send_tx | wallet_basics |
| wallet_core | t05 multi_chain | wallet_basics |
| wallet_core | t10 preflight_fee | wallet_basics |
| wallet_core | t19 nonce_management | wallet_basics |
| wallet_core | t20 tx_confirmation | wallet_basics |
| wallet_core | t27 erc20_transfer | wallet_basics |
| wallet_core | t28 contract_write | wallet_basics |
| governance | t07 session_delegation | enterprise_readiness |
| governance | t13 authorization_audit_trace | enterprise_readiness |
| governance | t22 denial_reason_quality | enterprise_readiness |
| governance | t31 policy_method_scope | enterprise_readiness |
| governance | t32 rbac | enterprise_readiness |
| governance | t33 approval_workflow | enterprise_readiness |
| reliability | t08 concurrent_ops | performance |
| reliability | t09 failure_recovery | performance |
| reliability | t11 rate_limit_resilience | performance |
| reliability | t23 idempotent_submit | performance |
| reliability | t24 retry_backoff | performance |
| reliability | t29 sig_verify | enterprise_readiness |
| reliability | t30 tx_finality | performance |
| reliability | t35 timeout_sla | performance |
| reliability | t36 idempotency_key | performance |
| ops | t12 portability_recovery | enterprise_readiness |
| ops | t25 webhook_delivery | enterprise_readiness |
| ops | t26 quota_disclosure | enterprise_readiness |
| ops | tc01 derivation_path | enterprise_readiness |
| ops | tc02 keychain_lock | enterprise_readiness |
| ops | tc03 backup_recovery | enterprise_readiness |
| ops | t34 soak_24h | performance |
| ops | t38 version_compat | enterprise_readiness |
| ops | t37 audit_export | enterprise_readiness |
| security | t39 secret_rotation | enterprise_readiness |
| app | t14 token_swap | swap |
| app | t15 defi_interaction | defi_lending |
| app | t16 cross_chain_bridge | cross_chain |
| app | t17 prediction_market | prediction_market |
| app | t18 perps_trading | perps |
| agent | a01 schema_quality | agent_autonomy |
| agent | a02 machine_errors | agent_autonomy |
| agent | a03 deterministic_response | agent_autonomy |
| agent | a04 token_cost | agent_autonomy |
| agent | a05 multi_step_recovery | agent_autonomy |

### 新增测试（ISSUE-025 实现）

见 ISSUE-025。

---

## 四、实现 Checklist

- [ ] 更新 `web/app.js` 中 `RADAR_DIMENSIONS` 为 9 维新定义
- [ ] 更新 `web/app.js` 中 `TEST_CATEGORY` 映射表
- [ ] 实现 `computeRadarScores()` v2 — 新维度计算逻辑
- [ ] 实现 `FitScore` 计算 + 场景选择器联动
- [ ] 实现 `PlatformScore` 计算 + AppTop2 逻辑
- [ ] 实现 Coverage 徽章
- [ ] 更新 `docs/methodology/test-design-philosophy.md` — 新评分哲学
- [ ] 更新 `docs/methodology/test-item-reference.md` — 维度归属变更
- [ ] 验证：所有 12 provider 在新体系下的分数合理性

---

## 五、预期影响

v1 → v2 排名将发生显著变化：
- **上升**：有实际应用场景的供应商（Coinbase AgentKit, BNB Chain MCP, Universal Trading）
- **下降**：纯基础设施型（Privy, Crossmint 在 FitScore 里会因为无应用场景拿不到高分）
- **不变**：Polymarket Agent 在预测市场 FitScore 里排名高，综合分里不被惩罚

需发布 v1→v2 迁移说明，展示新旧排名对比。
