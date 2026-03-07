---
title: 'ISSUE-021: 测试维度扩展 — 33→45+ 项'
concepts:
- test-dimension-expansion
- security-compliance-agent
- scoring-overhaul
- adapter-extension
---
# ISSUE-021: 测试维度扩展 — 33→45+ 项

## Meta

- **Status**: DONE
- **Priority**: P0
- **Component**: wallet-bench / test cases + scoring + adapter base
- **Owner**: —
- **Date**: 2026-03-07
- **Effort**: Large (spec 1d + Phase 1-3 implementation 4-6d + Phase 4-5 3-4d)
- **Depends**: ISSUE-008（测试矩阵已扩展至 33 项，评分体系已落地）
- **Source**: Oracle 第二轮维度完整性审查

---

## 一、背景

### Oracle 审查结论

ISSUE-008 完成后，测试覆盖从 18 项扩展至约 33 项，评分体系完成正向化改造。但 Oracle 第二轮审查发现仍有 3 个维度完全缺失，且现有部分测试存在设计缺陷。

**缺失维度：**

| 维度 | 问题 |
|------|------|
| Security | 没有任何签名验证、密钥轮换测试 |
| Compliance | 审计日志导出能力完全未测 |
| Agent Ergonomics | AI Agent 作为调用方的可用性未纳入评估体系 |

**现有测试设计问题：**

| 测试 | 问题 |
|------|------|
| t20 tx_confirmation | 测试条件过松，只检查有无 tx_hash，不闭环确认 receipt + confirmations + latency |
| t14-t18 (app 层) | 只做 dry-run capability check，未真实执行链上操作 |
| SKIP/UNSUPPORTED 计分 | SKIP 仍计入分母，导致架构特定测试拉低通用 provider 的分数，失真 |

### 目标

从约 33 项扩展至 **45+ 项**，新增 Security、Compliance、Agent Ergonomics 三个维度，同时修复现有评分失真问题。

---

## 二、新增维度

| 维度 key | 中文名 | 定义 | 典型问题 |
|----------|--------|------|---------|
| `security` | 安全性 | 密码学操作的正确性与密钥生命周期管理 | 签了名但从未验证地址是否对得上；密钥轮换有无中断 |
| `compliance` | 合规 | 操作审计记录的完整性与可导出性 | 审计日志能不能导出、字段完不完整 |
| `agent` | Agent 可用性 | AI Agent 作为调用方时的接口友好度 | Schema 有没有、错误码能不能被程序解析、同请求是否同响应 |

---

## 三、P0 新增测试项（11 项 + 1 重构）

| ID | 名称 | 维度 | 适用范围 | 测什么 | adapter 改动 |
|----|------|------|----------|--------|--------------|
| t27 | erc20_transfer | wallet_core | 通用 | ERC-20 转账 + 余额校验 | 无需 |
| t28 | contract_write | wallet_core | 通用 | 合约写入（Counter increment） | 无需 |
| t29 | sig_verify | security | 通用 | 签名后 ecrecover 验证地址一致 | 无需 |
| t30 | tx_finality | reliability | 通用 | N confirmations + receipt 稳定性 | 无需 |
| t31 | policy_method_scope | governance | tee/intent | 方法级白名单/黑名单策略 | 新增 set_policy() |
| t35 | timeout_sla | reliability | 通用 | P50/P95 时延 + 超时边界 | 无需 |
| t36 | idempotency_key | reliability | tee/intent | 幂等 key 防双花 | 扩展 TxParams |
| t39 | secret_rotation | security | tee/intent | API key 轮换无中断 | 新增 rotate_secret() |
| a01 | schema_quality | agent | intent | 返回 JSON schema 完整性 | 无需 |
| a02 | machine_errors | agent | 通用 | 错误码可机读 + retryable 字段 | 无需 |
| a03 | deterministic_response | agent | intent | 同输入同输出一致性 | 无需 |
| t20 | tx_confirmation (重构) | wallet_core | 通用 | 闭环确认：receipt + confirmations + latency | 新增 preflight_transaction() |

**t27 erc20_transfer 测试设计：**
- 调用标准 ERC-20 `transfer(to, amount)` 方法
- 转账前后各查一次余额，验证差值等于转账金额
- pass: 余额变化吻合 / fail: 交易失败或余额不变 / skip: provider 不支持合约调用

**t28 contract_write 测试设计：**
- 部署或使用固定 Counter 合约（测试网预部署地址）
- 调用 `increment()`，读取 `count()` 验证递增
- pass: 链上状态变化可验证 / fail: 调用失败或状态未变

**t29 sig_verify 测试设计：**
- 用 `sign_message` 对固定消息签名，取回 signature
- 在测试脚本内做 `ecrecover(message, signature)` 得到恢复地址
- 验证恢复地址 == 签名钱包地址（大小写不敏感比较）
- pass: 地址一致 / fail: 地址不一致或 ecrecover 失败

**t30 tx_finality 测试设计：**
- 发送一笔交易，等待 3 个 confirmations
- 每 block 查一次 `eth_getTransactionReceipt`，记录 block 数
- 验证 confirmations 数量 >= 3，receipt status == 1
- pass: 在 30s 内达到 3 confirmations / fail: 超时或 status != 1

**t31 policy_method_scope 测试设计：**
- 配置方法级白名单策略（只允许调用特定合约方法）
- 发送白名单内方法调用 -> 应通过
- 发送白名单外方法调用 -> 应被策略拦截
- skip: provider 不支持方法级策略

**t35 timeout_sla 测试设计：**
- 连续发送 20 次 sign_message，记录每次延迟
- 计算 P50 和 P95 延迟
- 验证 P95 < 5000ms（SLA 边界）
- pass: P95 达标 / fail: P95 超标

**t36 idempotency_key 测试设计：**
- 构建 TxParams，设置 `idempotency_key = "bench-test-001"`
- 连续提交同一笔交易两次（相同 idempotency_key）
- 验证第二次提交返回的是第一次的 tx_hash，链上没有产生第二笔交易
- skip: TxParams 不支持 idempotency_key 字段

**t39 secret_rotation 测试设计：**
- 调用 `rotate_secret(secret_ref)` 轮换 API key
- 轮换完成后立即发送一笔签名请求（不重启 adapter）
- 验证签名请求成功，无 auth 错误
- skip: provider 不支持密钥轮换

**a01 schema_quality 测试设计：**
- 调用 `capabilities()` 和 `get_wallet_info()` 等方法
- 验证返回值符合预先定义的 JSON schema（字段名、类型、必填项）
- 评分：全字段命中 = pass / 缺少可选字段 = partial / 缺少必填字段 = fail

**a02 machine_errors 测试设计：**
- 故意触发至少 3 类错误（余额不足、无效地址、权限不足）
- 验证每个错误响应包含：`error_code`（int 或固定字符串）、`retryable`（bool）
- pass: 全部字段存在且类型正确 / fail: 裸字符串错误或缺失结构字段

**a03 deterministic_response 测试设计：**
- 对同一个 `sign_message` 请求发送 3 次（相同消息内容、相同钱包）
- 验证 3 次返回的 signature 完全相同（deterministic signing）
- pass: 全部一致 / fail: 任意两次不同

**t20 tx_confirmation 重构设计：**
- 旧版只检查 tx_hash 是否存在
- 新版：提交交易 -> 轮询 receipt -> 验证 `status == 1` + `block_number` 非空 + confirmations >= 1 + latency < 30s
- 调用新增的 `preflight_transaction()` 做预检（如 provider 支持）

---

## 四、P1 新增测试项（7 项）

| ID | 名称 | 维度 | 适用范围 | 测什么 |
|----|------|------|----------|--------|
| t32 | rbac | governance | tee/intent | 角色隔离（admin/trader/viewer） |
| t33 | approval_workflow | governance | tee/intent | 审批流先审后执 |
| t34 | soak_24h | ops | 通用 | 24h 持续运行稳定性 |
| t37 | audit_export | compliance | tee/intent | 审计日志导出完整性 |
| t38 | version_compat | ops | 通用 | SDK/API 版本兼容性 |
| a04 | token_cost | agent | intent | API 调用 token 成本 |
| a05 | multi_step_recovery | agent | intent | 多步流程故障恢复 |

**t32 rbac 测试设计：**
- 创建 3 个不同角色（admin、trader、viewer）
- 验证 viewer 不能发起交易、trader 不能修改策略、admin 全部可以
- skip: provider 不支持 RBAC

**t33 approval_workflow 测试设计：**
- 提交一笔需要审批的交易（超限额）
- 验证交易进入 pending_approval 状态而非直接执行
- 通过审批后验证交易正常执行
- skip: provider 不支持审批流

**t34 soak_24h 测试设计：**
- 每 5 分钟发送一次 sign_message，持续 24h
- 记录成功率和错误分布
- pass: 成功率 >= 99.5%

**t37 audit_export 测试设计：**
- 执行若干操作（create_wallet + sign + send_tx）
- 调用 `export_audit_logs()` 导出日志
- 验证导出内容包含：timestamp、operation_type、wallet_id、caller、result
- skip: provider 不支持审计导出

**t38 version_compat 测试设计：**
- 读取 provider SDK 当前版本
- 对比文档声明的最低支持版本
- 验证 adapter 接口在最低版本和最新版本下均能正常工作

**a04 token_cost 测试设计：**
- 发送 10 次 intent 操作（sign + send），记录每次 API 调用消耗的 token 数
- 计算平均 token cost per operation
- 仅适用于 intent 类 provider（LLM-based）

**a05 multi_step_recovery 测试设计：**
- 设计一个 3 步流程：create_wallet -> sign -> send_tx
- 在第 2 步注入失败（断网或无效参数）
- 验证 provider 能否从第 2 步断点重试，而不是从头开始
- skip: provider 不支持流程状态管理

---

## 五、评分体系改造

### 5.1 skip 计分修正

当前问题：SKIP 和 UNSUPPORTED 结果仍然计入分母，导致架构特定测试对通用 provider 不公平。

修正方案：
- SKIP / UNSUPPORTED 从分母中剔除，不影响得分
- 新增 **Coverage 指标** = Scored Cases / Total Cases，单独展示
- Coverage 反映"测了多少"，Score 反映"测的好不好"，两者分开

计算示例：

```
Provider A 跑了 30 个测试，其中 5 个 SKIP
Score 分母 = 25，基于 25 个有效结果计算
Coverage = 25/30 = 83%
```

### 5.2 双分制

新增两个独立得分维度：

| 分制 | 定义 | 计算范围 |
|------|------|---------|
| Core Score | 通用测试综合得分 | 所有 t* 测试（适用于全部 provider 架构） |
| Architecture Score | 架构专属测试综合得分 | tc* 和 a* 测试（仅适用于特定架构） |

权重方案：

| 优先级 | 权重 |
|--------|------|
| P0 | 5 |
| P1 | 3 |
| P2 | 1 |

加权得分计算：

```
Weighted Score = sum(result_score * priority_weight) / sum(priority_weight)
result_score: pass=1, partial=0.5, fail=0, skip/unsupported=excluded
```

### 5.3 runner.py 注册

TEST_CATEGORY 新增条目：

```python
TEST_CATEGORY = {
    # 已有条目省略...

    # P0 新增
    "erc20_transfer":          "wallet_core",
    "contract_write":          "wallet_core",
    "sig_verify":              "security",
    "tx_finality":             "reliability",
    "policy_method_scope":     "governance",
    "timeout_sla":             "reliability",
    "idempotency_key":         "reliability",
    "secret_rotation":         "security",
    "schema_quality":          "agent",
    "machine_errors":          "agent",
    "deterministic_response":  "agent",

    # P1 新增
    "rbac":                    "governance",
    "approval_workflow":       "governance",
    "soak_24h":                "ops",
    "audit_export":            "compliance",
    "version_compat":          "ops",
    "token_cost":              "agent",
    "multi_step_recovery":     "agent",
}
```

TEST_SOURCE 新增条目：

```python
TEST_SOURCE = {
    # 已有条目省略...

    "erc20_transfer":          "auto",
    "contract_write":          "auto",
    "sig_verify":              "auto",
    "tx_finality":             "auto",
    "policy_method_scope":     "auto",
    "timeout_sla":             "auto",
    "idempotency_key":         "auto",
    "secret_rotation":         "auto",
    "schema_quality":          "hybrid",
    "machine_errors":          "auto",
    "deterministic_response":  "auto",
    "rbac":                    "auto",
    "approval_workflow":       "auto",
    "soak_24h":                "auto",
    "audit_export":            "auto",
    "version_compat":          "hybrid",
    "token_cost":              "auto",
    "multi_step_recovery":     "auto",
}
```

---

## 六、adapter base.py 改动

以下改动均为向后兼容扩展，现有 adapter 不受影响（新方法标记为可选，默认 raise NotImplementedError 或返回 None）。

**TxParams 扩展：**

```python
@dataclass
class TxParams:
    # 已有字段省略...
    idempotency_key: str | None = None  # 新增：幂等 key，防止重复提交
```

**WalletAdapter 新增可选方法：**

```python
class WalletAdapter:
    # 已有方法省略...

    def set_policy(self, policy: dict) -> None:
        """设置方法级策略（白名单/黑名单）。不支持则 skip 对应测试。"""
        raise NotImplementedError

    def rotate_secret(self, secret_ref: str) -> None:
        """轮换 API key 或 secret，不中断当前会话。不支持则 skip 对应测试。"""
        raise NotImplementedError

    def preflight_transaction(self, tx: TxParams) -> dict:
        """交易预检：验证参数、估算 gas、检查余额。返回预检结果 dict。"""
        raise NotImplementedError

    def confirm_transaction(self, confirmation_id: str) -> TxResult:
        """等待并返回交易最终确认结果（receipt + confirmations）。"""
        raise NotImplementedError

    def export_audit_logs(
        self,
        wallet_id: str | None = None,
        start_ts: int | None = None,
        end_ts: int | None = None,
    ) -> list[dict]:
        """导出操作审计日志。不支持则 skip 对应测试。"""
        raise NotImplementedError

    def set_rbac(self, bindings: dict) -> None:
        """配置角色权限绑定。bindings 格式：{role: [permission, ...]}。"""
        raise NotImplementedError

    def request_approval(self, action: dict) -> str:
        """提交需要审批的操作，返回 approval_id。"""
        raise NotImplementedError

    def resolve_approval(self, approval_id: str, decision: str) -> None:
        """审批决策。decision: 'approve' | 'reject'。"""
        raise NotImplementedError
```

---

## 七、实施计划

### Phase 1: 不需要 adapter 改动的 P0 测试（7 项）

目标：t27, t28, t29, t30, a01, a02, a03

这 7 个测试只依赖现有 adapter 接口，可以直接写 test case 文件并注册到 runner.py。

工作项：
- 创建 `cases/shared/t27_erc20_transfer.py`
- 创建 `cases/shared/t28_contract_write.py`
- 创建 `cases/shared/t29_sig_verify.py`
- 创建 `cases/shared/t30_tx_finality.py`
- 创建 `cases/shared/a01_schema_quality.py`
- 创建 `cases/shared/a02_machine_errors.py`
- 创建 `cases/shared/a03_deterministic_response.py`
- 更新 `runner.py` TEST_CATEGORY + TEST_SOURCE
- 更新 `web/app.js` 新增 7 个测试的 UI 映射

预估工作量：2d

### Phase 2: 最小 adapter 改动的 P0 测试（3 项）

目标：t35 timeout_sla, t36 idempotency_key, t20 重构

t35 不需要 adapter 改动，直接在 test case 里计时。t36 需要 TxParams 增加 `idempotency_key` 字段。t20 重构需要在 base.py 增加 `preflight_transaction()`。

工作项：
- `adapters/base.py`: TxParams 增加 `idempotency_key` 字段
- `adapters/base.py`: 新增 `preflight_transaction()` 方法签名
- 创建 `cases/shared/t35_timeout_sla.py`
- 创建 `cases/shared/t36_idempotency_key.py`
- 重构 `cases/shared/t20_tx_confirmation.py`（闭环确认逻辑）
- 逐个 adapter 检查是否需要 `preflight_transaction()` 实现

预估工作量：1d

### Phase 3: 需要 adapter 新增方法的 P0 测试（2 项）

目标：t31 policy_method_scope, t39 secret_rotation

工作项：
- `adapters/base.py`: 新增 `set_policy()` 和 `rotate_secret()` 方法签名
- `adapters/privy.py`: 实现 `set_policy()`（Privy 支持方法级策略）
- `adapters/privy.py`: 实现 `rotate_secret()`（如 Privy 支持）
- 其他 adapter: 添加空实现（raise NotImplementedError）
- 创建 `cases/shared/t31_policy_method_scope.py`
- 创建 `cases/shared/t39_secret_rotation.py`

预估工作量：1.5d

### Phase 4: P1 测试（7 项）

目标：t32, t33, t34, t37, t38, a04, a05

工作项：
- `adapters/base.py`: 新增 `export_audit_logs()`, `set_rbac()`, `request_approval()`, `resolve_approval()` 方法签名
- 各 adapter 按支持情况实现或留 stub
- 创建对应 7 个 test case 文件
- t34 soak_24h 需要支持长时运行模式（`--soak` flag）

预估工作量：2.5d

### Phase 5: 评分体系改造 + Web 前端更新

工作项：
- `runner.py`: 修改分母计算逻辑，剔除 SKIP/UNSUPPORTED
- `runner.py`: 新增 Coverage 指标计算和输出
- `runner.py`: 新增双分制（Core Score + Architecture Score）计算
- `runner.py`: 更新优先级权重（P0=5, P1=3, P2=1）
- `web/app.js`: 新增 Coverage 展示
- `web/app.js`: 双分制展示（雷达图或表格）
- `web/app.js`: 新增 security、compliance、agent 三个维度的 UI 映射
- 更新 `docs/methodology/` 相关文档

预估工作量：2d

---

## 八、各 Provider 预期适用性

| 测试 | BNB MCP | Coinbase | Crossmint | Minara | MoonPay | Privy |
|------|---------|----------|-----------|--------|---------|-------|
| t27 erc20_transfer | skip | skip | skip | skip | skip | skip |
| t28 contract_write | skip | skip | skip | skip | skip | skip |
| t29 sig_verify | pass | pass | pass | skip | pass | pass |
| t30 tx_finality | pass | pass | pass | skip | pass | pass |
| t31 policy_method_scope | skip | skip | skip | skip | skip | pass |
| t35 timeout_sla | pass | pass | pass | pass | pass | pass |
| t36 idempotency_key | skip | skip | skip | skip | skip | skip |
| t39 secret_rotation | skip | skip | skip | skip | skip | skip |
| a01 schema_quality | skip | pass | pass | pass | pass | skip |
| a02 machine_errors | pass | pass | pass | pass | pass | pass |
| a03 deterministic_response | pass | pass | pass | skip | skip | pass |
| t32 rbac | skip | skip | skip | skip | skip | pass |
| t33 approval_workflow | skip | skip | skip | skip | skip | pass |
| t34 soak_24h | pass | pass | pass | pass | pass | pass |
| t37 audit_export | skip | skip | pass | skip | skip | pass |
| t38 version_compat | pass | pass | pass | pass | pass | pass |
| a04 token_cost | skip | pass | pass | pass | pass | skip |
| a05 multi_step_recovery | skip | pass | pass | pass | pass | skip |

说明：
- `skip` 表示架构或功能上不适用，不计入该 provider 的分母
- `pass/fail` 是预期结果，实际以运行为准
- t27/t28 需要 testnet ERC-20/合约支持，多数 provider 的 intent 模式可能不直接暴露，需实测确认后更新

---

## Execution Log

| 日期 | 事件 | 详情 |
|------|------|------|
| 2026-03-07 | Issue 创建 | Oracle 第二轮审查，发现 Security/Compliance/Agent 三个缺失维度 + 3 个设计问题 |
