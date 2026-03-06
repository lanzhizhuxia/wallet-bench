---
title: 'ISSUE-001: 钱包 Skill 横向对比测试平台 — Adapter + Runner + Web 可视化'
concepts:
- wallet
- key-management
- signing
- TEE
- MPC
- agentic-wallet
- benchmark
- testnet
---
# ISSUE-001: 钱包 Skill 横向对比测试平台 — Adapter + Runner + Web 可视化

## Meta
- **Status**: MILESTONE_COMPLETE
- **Priority**: P1
- **Component**: wallet-bench (全新项目)
- **Owner**: —
- **Date**: 2026-03-05
- **Effort**: Medium (1-2 weeks)
- **Ref**: KarenZ 推文钱包/交易/支付类项目分析
- **Oracle Review**: R1 (架构+安全), R2 (测试维度), R3 (分批策略+类别专属测试) — 均 2026-03-05

## Background

基于 KarenZ 推文整理的钱包类项目分级（Tier 1-3），需要通过实际 demo 对各家钱包 Skill 的 Key 管理和签名能力进行横向对比测试，量化对比结果并通过 Web 页面展示。

### 架构分类（Oracle R3 建议按类别分批）

| 类别 | Provider | Key 托管模型 | 签名方式 | 链支持 |
|------|----------|-------------|---------|--------|
| **本地自托管 (Local)** | BNB Chain MCP | 用户提供 PRIVATE_KEY 环境变量 | MCP Server 本地签名 | BSC, opBNB (EVM) |
| | MoonPay Agents | 本地 BIP39 HD 钱包 | OS Keychain 加密 + 本地签名 | ETH, Base, Polygon, Arbitrum, Optimism, BNB, Avalanche, Solana, BTC, TRON |
| **API 托管 (Custodial)** | Bankr Skills | Bankr 持有密钥 | /agent/sign + /agent/submit 同步签名 | Base, ETH, Polygon, Unichain, Solana |
| **意图/委托 (Intent)** | Crossmint lobster.cash | lobster.cash 智能钱包 / PDA | Skill 声明意图, Pipeline 签名 | Solana, Base |
| | Daydreams / Lucid Agents | 本地裸私钥 / Thirdweb Engine / Lucid Platform | 取决于 Connector | Base, ETH, Solana |
| **TEE 托管 (TEE)** | Coinbase Agentic Wallets | TEE (AWS Nitro Enclave) | 服务端 TEE 内签名 | Base, ETH, Polygon, Arbitrum, Optimism, Solana |
| | Privy Agentic Wallets | TEE (AWS Nitro) + Key 分片 | P-256 授权密钥 + TEE 内重组签名 | EVM 全链 + Solana + Bitcoin/TRON/Stellar |
| **MPC + 智能钱包 (MPC+AA)** | Minara AI | TEE (Intel SGX/Privy) + MPC M-of-N | 分片密钥 + M-of-N 多服务授权 + ERC-4337 | EVM 多链 + Solana + Hyperliquid |

## Architecture

### Access Viability Gate（开工前必须完成）

每个 provider 开工前需验证以下 checklist，标记状态 `ready / blocked / unknown`：
- [ ] 官方文档可访问
- [ ] API Key / 账号 onboarding 路径确认
- [ ] Testnet / Sandbox 环境可用
- [ ] 一次 smoke call 成功（创建钱包 or 查询余额）

| Provider | 类别 | Status | 备注 |
|----------|------|--------|------|
| BNB Chain MCP | Local | **ready** ✅ | 只需 PRIVATE_KEY，无账号要求。13/13 测试通过 (9 PASS / 4 SKIP) |
| MoonPay Agents | Local | **ready** ✅ | `@moonpay/cli` — 非托管 BIP39 HD 钱包 + OS Keychain 加密 + MCP server。54 tools / 17 skills。支持 wallet create/sign/send + 10 链。需 email+hCaptcha 注册 (2026-03-05 调研) |
| Bankr | Custodial | **blocked** ❌ | 无公开文档/网站/API，疑似未上线 (2026-03-05 调研) |
| Crossmint | Intent | **ready** ✅ | REST API + Staging 环境。13/13 测试通过 (10 PASS / 3 SKIP) |
| Daydreams / Lucid | Intent | **blocked** ❌ | 开源框架非钱包服务，降优先级 (2026-03-05 调研) |
| Coinbase AgentKit | TEE | **ready** ✅ | Python SDK (v0.7.4), 三凭证 onboarding。13/13 测试通过 (9 PASS / 4 SKIP) |
| Privy | TEE | **ready** ✅ | REST API, 双凭证 onboarding。13/13 测试通过 (10 PASS / 3 SKIP) |
| Minara AI | MPC+AA | **ready** ✅ | minara CLI v0.2.9，custodial smart wallet。无签名原语但支持 transfer/swap。13/13 通过 (8 PASS / 5 SKIP) |

> **准入规则**：仅 `ready` 状态的 adapter 进入当前 Phase 实现。`unknown` 在 viability gate 通过后升级。被 `blocked` 的 provider 不阻塞其他批次。

### 目录结构（混合式，Oracle R3 建议）

```
adapters/                      # 钱包 Adapter 层（统一接口）
├── base.py                    # 抽象基类 WalletAdapter
├── bnbchain_mcp.py            # Local
├── moonpay.py                 # Local
├── bankr.py                   # Custodial
├── crossmint.py               # Intent
├── daydreams.py               # Intent
├── coinbase_agentkit.py       # TEE
├── privy.py                   # TEE
└── minara.py                  # MPC+AA

providers/                     # Provider 元数据清单
├── bnbchain_mcp.yaml          # class: local, capabilities, required_secrets, network_modes
├── moonpay.yaml
├── bankr.yaml
├── crossmint.yaml
├── daydreams.yaml
├── coinbase.yaml
├── privy.yaml
└── minara.yaml

cases/                         # 测试用例（共享 + 类别专属）
├── shared/                    # 所有 provider 必跑
│   ├── t01_key_generate.py
│   ├── t02_sign_message.py
│   ├── t03_sign_typed_data.py
│   ├── t04_send_tx.py
│   ├── t05_multi_chain.py
│   ├── t06_policy_enforcement.py
│   ├── t07_session_delegation.py
│   ├── t08_concurrent_ops.py
│   ├── t09_failure_recovery.py
│   └── t10_preflight_fee.py
└── class/                     # 类别专属（仅匹配类别的 provider 运行）
    ├── local/
    │   ├── tc01_derivation_path.py
    │   ├── tc02_keychain_lock.py
    │   └── tc03_backup_recovery.py
    ├── api_custodial/
    │   ├── tc01_idempotent_submit.py
    │   ├── tc02_session_lifecycle.py
    │   └── tc03_webhook_integrity.py
    ├── intent/
    │   ├── tc01_intent_schema.py
    │   ├── tc02_fulfillment_sla.py
    │   └── tc03_cancellation.py
    ├── tee/
    │   ├── tc01_attestation.py
    │   ├── tc02_failover_continuity.py
    │   └── tc03_policy_depth.py
    └── mpc_aa/
        ├── tc01_userop_lifecycle.py
        ├── tc02_bundler_paymaster.py
        └── tc03_quorum_threshold.py

runner.py                      # 测试编排器
config.yaml                    # 凭证/endpoint 配置（git-ignored）
config.example.yaml            # 配置模板

results/                       # 测试输出（git-ignored）
├── public_results.json        # 脱敏后的对比数据（可分享）
└── private_debug.json         # 含原始签名/地址/日志（不可分享）

web/                           # 前端展示（纯静态）
├── index.html
├── app.js
├── style.css
└── sample-result.json
```

**Runner 选择逻辑**：`run(provider) = cases/shared/* + cases/class/{provider.class}/*`
通过 `providers/<provider>.yaml` 中的 `class` 字段自动匹配，无需 hardcode if/else。

### Adapter 统一接口

```python
class WalletAdapter(ABC):
    # 基本信息
    name: str               # "Coinbase Agentic Wallets"
    arch_class: str         # "local" | "api_custodial" | "intent" | "tee" | "mpc_aa"

    # 链支持
    chains: list[str]       # ["ethereum", "base", "solana"]

    # 安全模型元数据（Oracle R1）
    custody_model: str      # "TEE" | "TEE+Shard" | "MPC" | "Local" | "API-Custodial" | "Smart-Wallet"
    signing_modes: list[str] # ["personal_sign", "eip712", "raw_tx"]
    submission_mode: str    # "client_submit" | "provider_submit" | "intent"

    # 核心方法
    async def create_wallet(self) -> WalletInfo: ...
    async def sign_message(self, message: str) -> SignResult: ...
    async def sign_typed_data(self, data: dict) -> SignResult: ...
    async def send_transaction(self, tx: TxParams) -> TxResult: ...
    def capabilities(self) -> dict[str, bool]: ...
    # Runner 使用 capabilities() 决定是否跳过不支持的测试项（SKIP_UNSUPPORTED）
    # 不支持的项标记为 "N/A-by-design"，不计入失败
```

### 测试体系

#### 共享测试（t01-t10，所有 provider 必跑）

**基线能力（t01-t05）** — 验证加密原语。intent/AA/custodial 模型测试"等效结果"。

| 用例 | 测试项 | Pass 条件 | 公平性说明 |
|------|--------|----------|-----------|
| t01_key_generate | 钱包创建 | 返回可用地址 + 耗时 | AA/intent 也有地址概念 |
| t02_sign_message | personal_sign / EIP-191 | 签名可验证 + 耗时 | custodial: API 返回签名即可 |
| t03_sign_typed_data | EIP-712 结构化签名 | 签名可验证 | intent 模型可标 N/A-by-design |
| t04_send_tx | 构建→签名→提交→确认 (testnet) | 链上确认 + 端到端延迟 | provider_submit 记录全流程延迟 |
| t05_multi_chain | 同一操作跨多链执行 | 各链均成功 + 对比延迟 | 评分按"声称支持链的实际可用率" |

**生产就绪（t06-t10，Oracle R2）** — 验证策略/委托/并发/恢复/费用控制。

| 用例 | 测试项 | Pass 条件 |
|------|--------|----------|
| t06_policy_enforcement | 支出限额/地址白名单拦截 | 允许 tx 成功；违规 tx 被拒 + 机器可读原因；重试不绕过 |
| t07_session_delegation | Agent 有限范围+时间权限 | 范围内成功；范围外失败；撤销在 SLA 内生效 |
| t08_concurrent_ops | N 个并行签名/支付 | 无重复支出，nonce/collision 正确，最终状态确定性 |
| t09_failure_recovery | 注入故障（RPC 超时、gas 不足、nonce 冲突） | 自动重试/reprice/cancel；终态正确且可审计 |
| t10_preflight_fee | 执行前费用估算 + 最大费用约束 | preflight 捕获余额不足；执行尊重 fee cap 或安全中止 |

#### 类别专属测试（Oracle R3 建议，仅匹配类别的 provider 运行）

**Local（本地自托管）** — BNB Chain MCP, MoonPay

| 用例 | 测试项 | Pass 条件 |
|------|--------|----------|
| tc01_derivation_path | 从助记词/私钥恢复，验证地址一致性 | 确定性地址匹配 |
| tc02_keychain_lock | Keychain 锁定时尝试签名 | 安全失败，日志/内存无明文泄露 |
| tc03_backup_recovery | 新设备/profile 恢复后签名验证 | 恢复后密钥可签名测试向量，身份匹配 |

**API-Custodial（API 托管）** — Bankr

| 用例 | 测试项 | Pass 条件 |
|------|--------|----------|
| tc01_idempotent_submit | 重放同一 idempotency key | 返回相同 operation id，链上仅一笔 |
| tc02_session_lifecycle | Token 过期/刷新期间的进行中操作 | 自动恢复，无孤立操作状态 |
| tc03_webhook_integrity | Webhook 签名验证 + 乱序送达 | 非法签名被拒；最终状态正确收敛 |

**Intent/Delegation（意图/委托）** — Crossmint, Daydreams/Lucid

| 用例 | 测试项 | Pass 条件 |
|------|--------|----------|
| tc01_intent_schema | 畸形意图 + 边界值 | 本地校验拦截，返回字段级错误 |
| tc02_fulfillment_sla | 全部成交/部分成交/超时 | 状态和数量正确，含时间戳和终态原因码 |
| tc03_cancellation | 执行前/执行中取消 | 取消 ID 发出，确认点后无后续 fill |

**TEE（TEE 托管）** — Coinbase AgentKit, Privy

| 用例 | 测试项 | Pass 条件 |
|------|--------|----------|
| tc01_attestation | 远程证明签名 + enclave measurement 验证 | 签名有效 + measurement 匹配白名单；mismatch 时会话被拒 |
| tc02_failover_continuity | 模拟 host 重启/轮换后重新签名 | 钱包身份持续性符合预期策略（无 key export 事件） |
| tc03_policy_depth | 多维度 allow/deny 规则（金额/目标/方法） | 拒绝操作返回确定性 policy code；允许操作正常执行 |

**MPC+AA（MPC + 智能钱包）** — Minara

| 用例 | 测试项 | Pass 条件 |
|------|--------|----------|
| tc01_userop_lifecycle | UserOperation: create → quorum sign → bundle → include | 完整状态转换，可检索 UserOpHash + tx hash |
| tc02_bundler_paymaster | 主 bundler 故障 + sponsor 上限边界 | fallback/retry 单效果（无重复执行），sponsor 遵守策略限额 |
| tc03_quorum_threshold | M-1 签名 vs M 签名 | M-1 不能执行；M 签名成功执行 |

### 评分模型（3 层，Oracle R2）

| 层级 | 权重 | 覆盖测试 | 衡量方式 |
|------|------|---------|---------|
| **能力覆盖 (Capability)** | 35% | t01-t05 + 等效结果映射 | 支持项数 / 总测试项 |
| **运维可靠性 (Reliability)** | 40% | t08-t10 + 成功率/p95延迟/重试次数 | 量化指标 |
| **治理与保障 (Assurance)** | 25% | t06, t07 + 安全模型证据 | 策略拦截率 + 证据字段 |

**评分规则**：
- `N/A-by-design` → 该层内重新分配权重，在兼容性矩阵中标记
- 展示 **类别内排行**（Local / Custodial / Intent / TEE / MPC+AA）+ **跨类综合**（带架构差异警告）
- DX 评分锚定可测量指标：time-to-first-success + 文档缺口数 + 错误信息清晰度
- 类别专属测试分数作为 **同类对比加分项**，不影响跨类综合分

### Web 展示

| 视图 | Phase | 说明 |
|------|-------|------|
| Feature Matrix | **Phase 1a** | 表格：行=测试项（共享+类别），列=钱包，单元格=✅/❌/⚠️/N/A + 延迟 |
| Detail Page | **Phase 1a** | 点击展开：安全模型、链支持、arch_class、submission_mode、共享+类别测试结果 |
| Radar Chart | Phase 2a | 3 层评分雷达图（Capability / Reliability / Assurance） |
| Latency Heatmap | Phase 2a | 热力图，颜色=延迟快慢 |

## Acceptance Criteria

### Phase 0 — Viability Gate（所有 Phase 的前置条件）

- [x] **AC-001-0a**: 完成所有 8 个 provider 的 Access Viability Gate checklist *(8/8 已标记: 4 ready, 4 blocked)*
- [x] **AC-001-0b**: `providers/*.yaml` 元数据清单建立（class, capabilities, required_secrets, network_modes）

### Phase 1a — 本地自托管类（BNB Chain MCP + MoonPay）

> 理由（Oracle R3）：最可控，无外部依赖，先跑通框架基础设施

- [x] **AC-001-1**: `adapters/base.py` 定义 `WalletAdapter` 抽象基类 + 数据结构
- [x] **AC-001-2**: `adapters/bnbchain_mcp.py` 实现，通过 testnet 完成共享测试
- [x] **AC-001-3**: `adapters/moonpay.py` 实现 *(16/16 通过：12 PASS / 4 SKIP。CLI subprocess + --json 输出。发现 3 个适配 bug，均已修复)*
- [x] **AC-001-4**: `cases/shared/` 实现 t01 + t02 基线测试
- [x] **AC-001-5**: `cases/shared/` 实现 t06-t10 生产就绪测试
- [x] **AC-001-6**: `cases/class/local/` 实现 tc01-tc03 类别专属测试
- [x] **AC-001-7**: `runner.py` 编排执行（shared + class 自动匹配），输出 public/private JSON
- [x] **AC-001-8**: Runner 内置 redaction 层 + RPC allowlist + mainnet abort
- [x] **AC-001-9**: `config.example.yaml` 模板
- [x] **AC-001-10**: `web/` Feature Matrix + Detail Page 视图
- [x] **AC-001-P1a-EXIT**: 本批所有 provider 通过共享测试 *(BNB Chain MCP 12P/4S + MoonPay 12P/4S，0 FAIL/0 ERROR)*

### Phase 1b — API 托管 + 意图/委托类（Bankr + Crossmint + Daydreams/Lucid）

> 理由：异步 API 状态机模式，webhook/幂等性/取消语义

- [ ] **AC-001-11**: `adapters/bankr.py` 实现 — **DEFERRED** *(blocked: 无公开文档/网站/API，疑似未上线)*
- [x] **AC-001-12**: `adapters/crossmint.py` 实现 *(daydreams 降优先级，非钱包服务)*
- [ ] **AC-001-13**: `cases/class/api_custodial/` 实现 tc01-tc03 *(blocked: Bankr)*
- [x] **AC-001-14**: `cases/class/intent/` 实现 tc01-tc03
- [x] **AC-001-15**: 共享测试 t03-t05 补全
- [ ] **AC-001-P1b-EXIT**: **PARTIAL** *(Crossmint 已达标；Bankr DEFERRED (blocked), Daydreams DEFERRED (非钱包服务))*

### Cross-Phase — Agent DX 评估模块（运行中追加）

> 理由：用户要求记录 AI agent 集成体验，为后来的 agent 提供避坑指南。不在原始 spec 中，属于 Discovery 类 auto-approved delta。

- [x] **AC-001-DX-1**: `evaluations/*.yaml` 评估数据文件，包含评分 (scores)、集成 bug 记录 (integration_bugs)、文档缺口 (doc_gaps)、agent 体验叙述 (agent_experience)
- [x] **AC-001-DX-2**: `evaluations/*.yaml` 包含详细 `agent_memo` 字段——给其他 agent 的集成备忘录（API 速查表、踩坑详解、轮询策略等）
- [x] **AC-001-DX-3**: `runner.py` 自动加载 `evaluations/{provider}.yaml` 并合并到输出 JSON
- [x] **AC-001-DX-4**: `web/app.js` + `style.css` 渲染 DX 评估面板（评分条、bug 表、doc gap 列表、agent 备忘录 markdown 渲染）

### Phase 2a — TEE 托管类（Coinbase AgentKit + Privy）

> 理由：TEE 信任边界行为，需 onboard CDP/Privy 账号

- [x] **AC-001-16**: `adapters/coinbase_agentkit.py` 实现 *(13/13 测试通过：9 PASS / 4 SKIP，发现 1 个集成 bug)*
- [x] **AC-001-17**: `adapters/privy.py` 实现 *(13/13 测试通过：10 PASS / 3 SKIP，发现 4 个集成 bug)*
- [x] **AC-001-18**: `cases/class/tee/` 实现 tc01-tc03 *(attestation + failover_continuity + policy_depth)*
- [x] **AC-001-19**: Web Radar Chart + Latency Heatmap 视图 *(Canvas 雷达图 + 色阶热力图，tab 切换)*
- [x] **AC-001-P2a-EXIT**: 本批通过共享测试 + 类别测试 *(Coinbase 9P/4S + Privy 10P/3S，全部 0 ERROR)*

### Phase 2b — MPC + 智能钱包类（Minara）

> 理由：ERC-4337 UserOp 生命周期最复杂，放最后

- [x] **AC-001-20**: `adapters/minara.py` 实现 *(13/13 通过：8 PASS / 5 SKIP。custodial wallet，无签名原语但支持 transfer/swap/account)*
- [ ] **AC-001-21**: `cases/class/mpc_aa/` 实现 tc01-tc03 *(Minara 为 custodial wallet，无 UserOp/bundler/quorum 能力，mpc_aa 类别测试不适用)*
- [x] **AC-001-22**: 全 provider 跨类 benchmark 运行 + 最终报告 *(6 provider 跨类对比报告: docs/COMPARISON-REPORT.md)*
- [ ] **AC-001-P2b-EXIT**: **PARTIAL** *(Minara adapter 完成但 mpc_aa 类别测试不适用；全量 benchmark 含 6 ready provider)*

### Phase 3 — 深度测试

- [x] **AC-001-23**: t11_rate_limit_resilience — 限流/配额耗尽行为 *(4 provider 全部 PASS: BNB 2ms, Privy 768ms, Coinbase 3675ms, Crossmint 20393ms)*
- [x] **AC-001-24**: t12_portability_recovery — 密钥导出/迁移/锁定披露 *(4 provider 全部 PASS: 验证 session restart 后钱包恢复和签名能力)*
- [x] **AC-001-25**: t13_authorization_audit_trace — 授权决策审计链 *(4 provider 全部 PASS: 验证审计字段完整性、capabilities 一致性、metadata 覆盖)*

## Phase 退出门（Oracle R3 建议）

每个 Phase 完成前必须满足：
1. 本批所有 `ready` provider 通过全部共享测试（t01-t10 中适用项）
2. 类别专属测试 ≥90% green
3. 无 P0 未知问题
4. 仅在发现共享测试 contract bug 时才回溯修改已完成的批次

## Non-Goals (本期不做)

- Tier 3 项目测试（无 Key 管理，无对比价值）
- Mainnet 交易（所有测试限定 testnet）
- 自动化 CI/CD（手动触发即可）
- 移动端适配（桌面浏览器优先）
- 企业级采购评估（不做 SOC 2 / 合规审计层面的对比）

## Safety Constraints

### 凭证安全
- `config.yaml` 必须在 `.gitignore`，凭证绝不入库
- `results/` 在 `.gitignore`，测试结果不入库
- Runner 内置 **redaction 层**：输出前自动扫描并移除 API key、auth header、private key、bearer token 等敏感字段

### 结果分级
- `public_results.json` — 脱敏后的对比数据，可安全分享（仅含测试状态、延迟、能力矩阵）
- `private_debug.json` — 含原始签名、地址、RPC 响应、错误堆栈（严禁分享）

### 网络安全
- Runner 启动时强制校验 chain ID，mainnet chain ID 直接 abort
- **RPC allowlist**：仅允许已知 testnet endpoint（Sepolia, Base Sepolia, Solana Devnet 等），未知 RPC URL 默认拒绝
- 所有 testnet 钱包使用 faucet 领取测试币，禁止转入真实资产

### Provider 限流
- 每个 adapter 配置 rate-limit/backoff 策略，避免测试触发 provider 封禁
- 记录重试次数到结果 JSON，作为可靠性指标

## Risk Assessment（Oracle R3）

**不分批（monolithic）的风险**：
- 高调度耦合：一个 provider blocked（access/auth/法律），整个里程碑停滞
- 调试模糊：共享 contract bug 与架构特定行为混在一起，减慢排查
- 抽象债：被迫用"one-size" adapter API 过拟合最简单类别，隐藏类别特定回归

**分批策略的注意事项**：
- 共享测试不能编码类别特定假设（如假设所有 provider 都有裸签名）
- 每个 provider 只归一个 primary class，避免重复 ownership
- Phase 退出门提前锁定，否则分批会退化为 ad hoc 并行

## Oracle Review Log

| 轮次 | 日期 | 审核范围 | 关键发现 | 状态 |
|------|------|---------|---------|------|
| R1 | 2026-03-05 | 架构 + 安全 + 可行性 | BLOCK: 结果敏感数据泄露; CONCERN: adapter 接口太 EOA 中心, Phase 1 缺本地基线 | ✅ 已整合 |
| R2 | 2026-03-05 | 测试维度 + 测试用例 | CONCERN: 缺生产就绪测试(策略/并发/恢复), 评分模型偏简单, 对 intent/AA 不公平 | ✅ 已整合 |
| R3 | 2026-03-05 | 分批策略 + 类别专属测试 | 推荐按架构类别分 4 批开发; 新增 5 类×3 个专属测试; 混合目录结构 cases/shared + cases/class | ✅ 已整合 |

## Execution Log

| 日期 | 事件 | 详情 |
|------|------|------|
| 2026-03-05 | Phase 1a 完成 | BNB Chain MCP adapter + 全部基础设施 (base, runner, web, 13 tests)。发现 4 个集成 bug (参数名/Decimal/返回字段/单位)，均为 our_code |
| 2026-03-05 | Phase 1b 可行性调研 | Bankr → blocked (无公开资料); Crossmint → ready; Daydreams → 降优先级 (框架非钱包服务) |
| 2026-03-05 | Crossmint adapter 完成 | Intent 类 adapter + tc01-tc03。发现 3 个集成 bug (EIP-712 domain 严格/wei 单位/422 revert)。t03-t05 共享测试补全 |
| 2026-03-05 | DX 评估模块上线 | 新增 evaluations/ 目录，含评分 + agent_memo 详细备忘录。Web UI 渲染评估面板 + markdown memo |
| 2026-03-05 | Phase 2a: Privy adapter 完成 | TEE 类 adapter + tc01-tc03 类别测试。13/13 通过 (10 PASS / 3 SKIP)。发现 4 个 bug: Cloudflare 拦截、caip2 不一致、snake_case 命名、chainId 位置。签名延迟 ~170ms（比 Crossmint 快 60x） |
| 2026-03-05 | Phase 2a: Coinbase AgentKit 完成 | 用户提供 Wallet Secret（EC P-256 DER）后解锁。13/13 通过 (9 PASS / 4 SKIP)。发现 1 个 bug: value 必须是 int 不能是 hex string。Onboarding 需三个独立凭证（API Key ID + Secret + Wallet Secret），是所有 provider 中最重的 |
| 2026-03-05 | Phase 2a EXIT: Web 可视化完成 | 新增 Radar Chart（Canvas 五维雷达图: Capability/Reliability/DX/Speed/Coverage）+ Latency Heatmap（色阶热力图 + 均值统计）。Tab 导航切换三个视图。4 provider 数据齐全 |
| 2026-03-05 | Phase 3 深度测试完成 | 新增 t11 限流恢复 + t12 可移植性恢复 + t13 授权审计链。4 provider 全部 16/16 PASS (排除 SKIP)。Runner 改为聚合写入模式 |
| 2026-03-05 | 跨类对比报告更新 | docs/COMPARISON-REPORT.md 从 Round 1 (2 provider) 更新为完整版 (4 provider)。含综合评分、延迟对比、Bug 模式归纳、架构选型建议 |
| 2026-03-05 | **阶段性完成 (MILESTONE_COMPLETE)** | 4 provider × 16 tests 全部通过。Phase 1a/1b/2a/3 + DX 评估 + 跨类报告均已完成。剩余 MoonPay/Bankr/Minara 被外部依赖阻塞，待信息突破后再追加 |
| 2026-03-05 | Viability Gate 调研完成 | MoonPay Agents → **ready** (`@moonpay/cli` 非托管 HD 钱包，54 tools/17 skills，支持 sign+send+MCP); Minara → blocked (custodial 无签名原语); Daydreams → blocked (框架非钱包)。8/8 provider 已标记 (5 ready / 3 blocked)，AC-001-0a 完成 |
| 2026-03-05 | ISSUE-002 收尾: Blocked providers DEFERRED | 正式标记 AC-001-11 (Bankr), AC-001-20/21 (Minara), Daydreams 为 DEFERRED。剩余 blocked provider 不阻塞项目关闭 |
| 2026-03-05 | MoonPay Agents adapter 完成 | @moonpay/cli v0.12.11，CLI subprocess + --json 模式。16/16 通过 (12 PASS / 4 SKIP)。发现 3 个适配 bug（value=0 拒绝、非确定性钱包、tc02 硬编码），均已修复。Phase 1a EXIT gate 达标 |
| 2026-03-05 | Minara AI adapter 完成 | minara CLI v0.2.9，custodial smart wallet。文本解析适配（--json 不输出 JSON）。13/13 通过 (8 PASS / 5 SKIP)，0 bug。mpc_aa 类别测试不适用（无 UserOp/bundler/quorum 能力）。6 provider 全部在线 |
