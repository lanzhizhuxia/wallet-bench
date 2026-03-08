# ISSUE-025 — 新增测试项：App 场景扩充 + Agent 自主性 + 性能基准

**Status**: OPEN  
**Priority**: P0  
**Created**: 2026-03-08  
**Depends on**: ISSUE-024（维度定义）  
**Blocks**: ISSUE-026（Dashboard 需要新数据）

---

## 背景

ISSUE-024 定义了 9 维雷达体系，但现有 45 项测试中：
- 5 个应用场景各只有 1 项测试，远不够评估实际策略执行能力
- Agent 自主性缺少工具发现、零样本执行、Function Calling 兼容等关键测试
- 无独立性能基准测试（延迟、吞吐、冷启动）

本 ISSUE 补齐这些测试项。

---

## 一、Swap 场景扩充（6 项新增）

| 测试 ID | 名称 | 测试内容 | 通过标准 |
|---------|------|---------|---------|
| `s01` | `route_discovery` | 能否自动发现并选择 ≥2 个协议的最优路径 | 返回至少 2 条路由 + 最优选择 |
| `s02` | `slippage_guard` | 超滑点时安全失败或自动调整 | 不执行超阈值交易 OR 自动降低量 |
| `s03` | `mev_protection` | 是否支持 private relay / 防三明治攻击 | 有 MEV 保护路径可用 |
| `s04` | `minimal_approve` | 能精确 approve 时不给 unlimited | approve 金额 = 实际需要量 |
| `s05` | `post_revoke` | 完成后自动 revoke 或降低 allowance | 操作后 allowance 归零或降低 |
| `s06` | `unsafe_approve_detect` | 识别可疑的 permit/approve 并阻止 | 检测到异常时拒绝执行 |

**维度归属**: `swap`  
**现有 t14 (token_swap) 保留**，总计 swap 维度 7 项测试。

---

## 二、DeFi 借贷场景扩充（1 项新增）

| 测试 ID | 名称 | 测试内容 | 通过标准 |
|---------|------|---------|---------|
| `d01` | `farm_combo` | approve → swap → stake → claim 端到端 | 全链路成功 + 耗时 < SLA |

**维度归属**: `defi_lending`  
**现有 t15 (defi_interaction) 保留**，总计 2 项。

---

## 三、跨链场景扩充（1 项新增）

| 测试 ID | 名称 | 测试内容 | 通过标准 |
|---------|------|---------|---------|
| `x01` | `arb_atomicity` | 两腿套利路由执行，部分失败时不卡资金 | 双腿全成功 OR 单腿失败时资金安全回滚 |

**维度归属**: `cross_chain`  
**现有 t16 (cross_chain_bridge) 保留**，总计 2 项。

---

## 四、预测市场场景扩充（1 项新增）

| 测试 ID | 名称 | 测试内容 | 通过标准 |
|---------|------|---------|---------|
| `m01` | `market_combo` | 查询赔率 → 下注 → 平仓/赎回 端到端 | 全链路成功 |

**维度归属**: `prediction_market`  
**现有 t17 (prediction_market) 保留**，总计 2 项。

---

## 五、永续合约场景（暂不扩充）

现有 t18 (perps_trading) 保留，1 项。后续按需扩充。

---

## 六、Agent 自主性扩充（6 项新增）

| 测试 ID | 名称 | 测试内容 | 通过标准 |
|---------|------|---------|---------|
| `ag01` | `tool_discovery` | 不看文档能否枚举可调用方法和参数 | 返回完整方法列表 + 参数 schema |
| `ag02` | `zero_shot_exec` | 自然语言目标 → 可执行计划的成功率 | ≥ 1 个合理执行计划 |
| `ag03` | `error_self_recovery` | 收到原始错误后，换参数重试成功率 | 至少 1 次自动修正后成功 |
| `ag04` | `multi_step_plan` | approve → swap → bridge → stake 计划正确性 | 步骤顺序正确 + 依赖关系正确 |
| `ag05` | `context_efficiency` | 描述 API 需要多少 token | ≤ 2000 tokens 描述完整 API |
| `ag06` | `fc_compatibility` | OpenAI function calling + MCP 协议兼容性 | schema 格式正确 + 调用成功 |

**维度归属**: `agent_autonomy`  
**现有 a01-a05 保留**，总计 11 项。

---

## 七、性能基准测试（6 项新增）

| 测试 ID | 名称 | 测试内容 | 通过标准 |
|---------|------|---------|---------|
| `p01` | `tx_latency` | 交易提交延迟 p50/p95/p99 | p95 ≤ 1.2s |
| `p02` | `burst_throughput` | 30s/120s 窗口内突发吞吐 | ≥ 5 tx/s 持续 30s |
| `p03` | `cold_start` | 初始化到首笔交易延迟 | ≤ 3s |
| `p04` | `gas_accuracy` | Gas 估算精度（绝对误差百分比） | 中位误差 ≤ 15% |
| `p05` | `mempool_latency` | Mempool 事件延迟对比参考节点 | ≤ 250ms |
| `p06` | `bridge_completion` | 跨链桥完成时间 p50/p95 | p95 ≤ 20min |

**维度归属**: `performance`  
**现有 t08/t09/t11/t23/t24/t30/t34/t35/t36 重归属到 performance**，总计 15 项。

---

## 八、测试总数

| 维度 | 现有 | 新增 | 合计 |
|------|------|------|------|
| swap | 1 | 6 | **7** |
| defi_lending | 1 | 1 | **2** |
| cross_chain | 1 | 1 | **2** |
| prediction_market | 1 | 1 | **2** |
| perps | 1 | 0 | **1** |
| agent_autonomy | 5 | 6 | **11** |
| performance | 9 | 6 | **15** |
| wallet_basics | 10 | 0 | **10** |
| enterprise_readiness | 16 | 0 | **16** |
| **合计** | **45** | **21** | **66** |

---

## 九、实现 Checklist

### Phase 1 — Swap + Agent（优先）
- [ ] 实现 s01-s06（swap 场景 6 项）
- [ ] 实现 ag01-ag06（agent 自主性 6 项）
- [ ] 在 `runner.py` 中注册新测试
- [ ] 在 `adapters/base.py` 中定义新测试方法签名
- [ ] 为 12 个 adapter 添加新测试的 stub/实现

### Phase 2 — Performance
- [ ] 实现 p01-p06（性能基准 6 项）
- [ ] 设计延迟采集框架（多次运行取统计值）

### Phase 3 — 其他场景
- [ ] 实现 d01（DeFi 借贷组合）
- [ ] 实现 x01（跨链套利原子性）
- [ ] 实现 m01（预测市场组合）

---

## 十、注意事项

- 新测试对于不支持该场景的供应商，状态应为 `not_applicable`，不进入评分分母
- 性能测试需要多次运行取统计值，runner.py 已支持 `--runs N`
- Agent 自主性测试可能需要引入 LLM 调用来模拟 Agent 行为（ag02, ag03, ag04）
