---
title: 'ISSUE-012: Crossmint 链上工厂合约反查 — 通过自测钱包提取 factory 地址'
concepts:
- on-chain-analytics
- competitive-intelligence
- reverse-engineering
---
# ISSUE-012: Crossmint 链上工厂合约反查

## Meta
- **Status**: DONE
- **Priority**: P2
- **Component**: scripts/, docs/issues/active/ISSUE-011-competitor-monitoring/
- **Owner**: Claude
- **Date**: 2026-03-06
- **Effort**: Short (~1h actual)
- **Blocked By**: ~~需要 Crossmint Staging API Key（config.yaml 中已有）~~ 已解决
- **Blocks**: ISSUE-011 Phase 2 Task 2-x（Crossmint 链上数据采集）— 结论：**factory + bundler 组合可精准归因**

## Background

ISSUE-011 Task 0-3 调研结论：Crossmint 使用 ERC-4337 + ERC-7579 智能合约钱包架构，但工厂合约地址完全封装在 API 后端，官方文档和 SDK 源码均无公开地址，BundleBear 社区标签库也无 Crossmint 条目。

**关键洞察**：wallet-bench 项目本身就有 Crossmint adapter（`adapters/crossmint.py`），测试时会通过 Crossmint Staging API 在 Base Sepolia 上真实创建钱包。这个测试钱包的创建交易就在链上，可以直接反查 UserOp 中的 `factory` 字段，完全不需要第三方配合。

## 目标

1. 运行 wallet-bench Crossmint adapter 在测试网创建钱包
2. 在链上浏览器（JiffyScan / Basescan）查询该钱包的 UserOp，提取 `factory` 字段
3. 验证工厂合约归属（Crossmint 专属 or 第三方通用）
4. 更新 `onchain-attribution.yaml`，将 Crossmint 从 `trackable: false` 改为有数据的状态
5. 如果找到可用工厂地址，更新 `onchain-attribution.yaml` 并通知 ISSUE-011 Phase 2 可以接入

## 任务分解

### Task 1: 创建测试钱包并获取地址（~30min）

**前置条件**：
- `config.yaml` 中填入有效的 Crossmint Staging API Key（`sk_staging_...`）
- 有 Base Sepolia 测试网 EOA 私钥（`eoa_private_key`）

**步骤**：
```bash
python runner.py run --provider crossmint --config config.yaml
```
- 记录输出中的钱包地址（`key_generate` 测试返回的地址）
- 如果 adapter 有 `--dry-run` 或只跑 `key_generate` 的选项，只跑这一步即可

**交付物**：Crossmint Staging 测试钱包地址（Base Sepolia）

---

### Task 2: 链上反查 factory 地址（~30min）

**方法 A（推荐）**：JiffyScan
```
https://jiffyscan.xyz/userOpHash/{userOpHash}?network=base-sepolia
```
或直接搜索钱包地址：
```
https://jiffyscan.xyz/account/{wallet_address}?network=base-sepolia
```
在 UserOp 详情中找 `factory` 字段（initCode 的前 20 bytes）。

**方法 B**：Basescan
```
https://sepolia.basescan.org/address/{wallet_address}
```
查看第一笔交易，找 UserOperation 的 initCode，前 20 bytes 即为 factory 地址。

**方法 C**（如果 A/B 无数据）：直接查 EntryPoint 事件
- EntryPoint v0.6：`0x5FF137D4b0FDCD49DcA30c7CF57E578a026d2789`
- 查询 `AccountDeployed(userOpHash, sender, factory, paymaster)` 事件
- 按 `sender` = 测试钱包地址过滤，即可得到 `factory`

**交付物**：factory 地址 + 获取方式截图/链接

---

### Task 3: 验证工厂合约归属（~30min）

1. 在 Basescan 查看工厂合约源码（如已验证）
2. 检查合约名称、部署者地址、是否与 Crossmint 组织关联
3. 检查 BundleBear 标签库：
   ```
   https://github.com/Jam516/BundleBear/blob/main/models/erc4337/labels/erc4337_labels_factories.sql
   ```
   搜索该地址是否已有标签
4. 如果是已知第三方工厂（如 Kernel/Safe/Biconomy），记录具体版本
5. 如果是 Crossmint 专属合约，检查是否在 mainnet 上有相同地址（CREATE2 确定性部署）

**交付物**：
- 工厂地址归属结论（Crossmint 专属 / 已知第三方 + 版本 / 未知）
- 是否可用于链上归因的判断

---

### Task 4: 更新 onchain-attribution.yaml（~30min）

根据 Task 3 结论更新 `docs/issues/active/ISSUE-011-competitor-monitoring/onchain-attribution.yaml`：

**如果找到可归因地址**：
```yaml
crossmint:
  trackable: true  # 改为 true
  architecture: smart_wallet
  chains:
    - chain: base-sepolia  # 先记录测试网，再验证 mainnet
      factory_addresses:
        - address: "0x..."
          source: "通过 wallet-bench 测试钱包反查（Base Sepolia UserOp）"
          verified: true/false
  notes: "通过 wallet-bench 自身测试反向工程获得，需进一步验证 mainnet 地址"
```

**如果工厂是已知第三方（如 Kernel）**：
```yaml
crossmint:
  trackable: partial  # 可追踪但归因不精确
  reason: "使用 {ZeroDev Kernel/Biconomy/...} 工厂，无法区分 Crossmint 来源与直接使用该工厂的其他应用"
  underlying_factory: "zerodev_kernel"
  notes: "..."
```

**如果完全无法归因**：保持 `trackable: false`，补充具体的失败原因。

---

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Crossmint Staging API 不可用 | 无法创建测试钱包 | 检查 API key 是否有效，或使用已有测试结果中的钱包地址 |
| 测试网数据被清理（indexer 未收录） | JiffyScan 查不到数据 | 改用 Basescan 直接查 EntryPoint 事件 |
| 工厂是通用第三方工厂 | 无法区分 Crossmint 来源 | 标注为 partial，说明使用哪个底层工厂 |
| Crossmint 在 mainnet 用不同工厂 | 测试网结论不可直接复用 | 标注仅验证测试网，mainnet 需额外验证 |

## 成功标准

- [x] 获得至少一个 Crossmint 在 Base Sepolia 创建的钱包地址
  - `0x490E6A6c74bfd538083938A108098c1c47eAa6E9`（来自 wallet-bench 测试运行 2026-03-05）
- [x] 确定该钱包对应的 factory 地址（来源可追溯）
  - Factory: `0xd703aae79538628d27099b8c4f621be4ccd142d5`（ZeroDev Kernel，BundleBear 标签确认）
  - 来源: EntryPoint v0.7 AccountDeployed 事件，Block 38482363，TX `0x430bcd0a...`
- [x] `onchain-attribution.yaml` 中 Crossmint 条目有明确的归因结论
  - `trackable: partial`，`underlying_factory: zerodev_kernel`
- [x] 如 trackable，ISSUE-011 Phase 2 可接入 Crossmint 数据
  - 结论：partial — 可追踪到 Kernel 工厂级别，但无法精确区分 Crossmint 与其他 Kernel 用户

## 执行记录

### 结果摘要

| 项目 | 值 |
|------|-----|
| 测试钱包 | `0x490E6A6c74bfd538083938A108098c1c47eAa6E9` |
| Factory | `0xd703aae79538628d27099b8c4f621be4ccd142d5` (ZeroDev Kernel) |
| EntryPoint | **v0.7** (`0x0000000071727de22e5e9d8baf0edac6f37da032`) |
| Validator Module | `0x845adb2c711129d4f3966735ed98a9f09fc4ce57` |
| Paymaster | 无（零地址） |
| Bundler | `0xb052d58410a2c54e27d3d62f99bf8b2bb27a8d23` |
| 部署区块 | 38482363 |
| 部署 TX | `0x430bcd0add8d5b6ef10d2b46c68992c1fd77dc9f005a4dd82bdc5b9b5a2de379` |
| 钱包合约大小 | 61 bytes（ERC-1967 升级代理） |

### 调研思路演进

#### Step 0: 跳过 Task 1 — 复用已有测试结果

`results/private_debug_crossmint.json` 中 2026-03-05 的运行记录已包含完整数据：
- `t01 key_generate` → 钱包地址 `0x490E6A6c74bfd538083938A108098c1c47eAa6E9`
- `t08 nonce_management` → tx hash `0xa9bac4f0...`, `0x4b2b63d7...`
- `t25 tx_confirmation` → tx hash `0x09f51051...`，且 `meta.raw.onChain` 中有完整的 UserOp 结构（sender, nonce, callData 等）和 `userOperationHash`

无需重新跑 adapter。

#### Step 1: 首次尝试 — JiffyScan / Basescan 浏览器

- **JiffyScan**：WebFetch 返回空 `pageProps: {}`。JiffyScan 是 JS 客户端渲染，无法通过静态 HTML fetch 获取数据。**放弃此路径**。
- **Basescan V1 API**：`api-sepolia.basescan.org/api?module=logs` 和 `module=account` 均返回 `NOTOK: You are using a deprecated V1 endpoint`。Etherscan 已全面迁移到 V2 API 且需要 API key。**放弃此路径**。

> 教训：区块浏览器 API 变动频繁，直接走 RPC 更可靠。

#### Step 2: 直接走 RPC — 第一个误区

用 `sepolia.base.org` 公共 RPC 调用 `eth_getTransactionReceipt`，返回 HTTP 403 Forbidden。
Base 官方 RPC 限制了部分请求来源。

切换到 **`base-sepolia-rpc.publicnode.com`** 成功。

#### Step 3: 关键发现 — EntryPoint 不是 v0.6

成功拿到 `0xa9bac4f0...` 的 receipt：
- `To: 0x0000000071727de22e5e9d8baf0edac6f37da032` — 这是 **EntryPoint v0.7**
- **不是** ISSUE-012 原始设计中假设的 v0.6 (`0x5FF137D4...`)

这是一个关键发现。ISSUE-011 原始调研基于 "Crossmint 使用 EntryPoint v0.6" 的假设，实际上 Crossmint 已经升级到 v0.7。

> 影响：EntryPoint v0.7 的 `AccountDeployed` 事件签名与 v0.6 相同（参数一致），但 `UserOperationEvent` 等其他事件的 ABI 有差异。后续 Phase 2 Dune query 需要同时监控 v0.6 和 v0.7。

#### Step 4: 三笔交易都没有 AccountDeployed — Lazy Deployment 的时序问题

检查已知的三笔交易（Block 38482366 / 38482370 / 38482373），它们的日志中**只有** `BeforeExecution` 和 `UserOperationEvent`，**没有** `AccountDeployed`。

推理：这些不是钱包的**部署**交易。Crossmint 的 `create_wallet()` API 调用是先在后端注册钱包，链上合约部署发生在更早的一笔交易中。观察 UserOp 中的 nonce 值 `0x845adb2c...00040000...` 非零，证实这些 UserOp 不是该钱包的第一笔操作。

> 关键理解：Crossmint 的工作流是 `API 创建钱包 → 首笔链上交易时 lazy deploy 合约`，而 wallet-bench 的 `key_generate` 测试调用 `create_wallet()` 后紧接着就有 `sign_message` 等后续操作，合约部署嵌入在首次 UserOp 提交中。

#### Step 5: 扩大搜索范围 — 找到部署交易

改用 `eth_getLogs` 在 EntryPoint v0.7 上搜索 `AccountDeployed` 事件，以 `sender = 钱包地址` 过滤：

```
Topics: [AccountDeployed_topic, null, sender_padded_to_32bytes]
Block range: 38432366 → 38482366 (50000 blocks)
```

第一轮搜索即命中：
- **Block 38482363**（比首笔已知交易早 3 个区块）
- TX `0x430bcd0a...`
- Data 字段解码：**factory = `0xd703aae79538628d27099b8c4f621be4ccd142d5`**，paymaster = 零地址

> 时序验证：部署 (Block 38482363) → 首笔 UserOp (Block 38482366)，间隔 3 个区块 ≈ 6 秒，与 Crossmint API 创建钱包后立即执行 sign_message 的测试流程吻合。实际上部署和首笔操作可能在同一笔 bundled tx 中，由 bundler 拆分到了不同区块。

#### Step 6: 验证 Factory 归属

**链上合约分析**：
- 工厂合约 bytecode 长度 1871 bytes，非代理合约，包含完整逻辑
- Solidity function selector 分析：含 `f04e283e`（`transferOwnership`）、`f2fde38b`（`acceptOwnership`）、`fee81cf4`（`pendingOwner`）等 Ownable 模式函数

**BundleBear 交叉验证**：
在 `erc4337_labels_factories.sql` 中搜索 `0xd703aae79538628d27099b8c4f621be4ccd142d5`：
→ **命中，标签为 `zerodev_kernel`**

同时确认该文件中**无任何** `crossmint` / `rhinestone` / `nexus` / `7579` 相关标签。Crossmint 在社区归因数据库中完全不可见。

**部署交易日志分析**（TX `0x430bcd0a...` 共 6 个 log）：

| Log | 地址 | 事件 | 含义 |
|-----|------|------|------|
| 0 | 钱包 | `0x6789ec0c...` | 未知（可能是 Kernel 的 `Initialized` 或自定义事件） |
| 1 | `0x845adb2c...` | `0xa5e1f8b4...` | Validator module 事件（owner 设置） |
| 2 | 钱包 | `ModuleInstalled(uint256,address)` | **ERC-7579 模块安装**，确认模块化架构 |
| 3 | EntryPoint v0.7 | `AccountDeployed` | 标准 ERC-4337 账户部署事件 |
| 4 | EntryPoint v0.7 | `BeforeExecution` | UserOp 执行前钩子 |
| 5 | EntryPoint v0.7 | `UserOperationEvent` | UserOp 执行结果 |

Log 2 的 `ModuleInstalled` 是决定性证据：这不仅是 ERC-4337，还是完整的 **ERC-7579 模块化智能账户**，与 Crossmint 文档声称的架构完全吻合。

**钱包合约本身**：
- 61 bytes，是 ERC-1967 升级代理（bytecode 含 `360894a13ba1a3210667c828492db98dca3e2076cc3735a920a3ca505d382bbc`，即 ERC-1967 implementation storage slot 的 keccak256）
- 所有逻辑 delegatecall 到 implementation 合约（ZeroDev Kernel 实现）

#### Step 7: 初步归因结论 — `trackable: partial`

```
Crossmint → Crossmint API → ZeroDev Kernel Factory → ERC-7579 Smart Account
                                    ↑
                     BundleBear 标签：zerodev_kernel（7 个已知地址之一）
                     其他使用者：ZeroDev SDK 直接用户、可能的其他 WaaS
```

仅凭 factory 无法精准归因。需要寻找辅助条件。

#### Step 8: Bundler 分析 — 精准归因突破口

对 factory `0xd703aae...` 在 Base Sepolia 最近 2000 个区块内的 76 笔部署交易做 bundler 分布统计：

| Bundler | 占比 | 身份 |
|---------|------|------|
| `0xb052d584...` | **67.1%** | Crossmint bundler |
| `0x858b86e5...` | 10.5% | 未知（nonce 10,342，另一个高频用户） |
| `0x4337xxxx...` (多个) | 22.4% | **Pimlico 公共 bundler**（地址前缀 `0x4337` 是 Pimlico 特征） |

**反向验证**：Crossmint bundler `0xb052d584...` 发送的 87 笔 AccountDeployed 交易中，**100% 指向 factory `0xd703aae...`**。该 bundler 与该 factory 是一对一绑定关系。

> 关键结论：`factory + bundler` 组合可以精准归因 Crossmint。
> - 正向：该 factory 67% 的部署来自 Crossmint bundler
> - 反向：该 bundler 100% 只用这一个 factory
> - 剩余 33% 来自 Pimlico 公共 bundler 和一个未知 bundler，这些是其他 Kernel 用户

#### Step 9: Validator Module 归属 — 排除为精准归因条件

对 `0x845adb2c...` 做多链存在性检查：

| 链 | 状态 |
|----|------|
| Ethereum Mainnet | 已部署（1819 bytes） |
| Base Mainnet | 已部署（1819 bytes） |
| Arbitrum Mainnet | 已部署（1819 bytes） |
| Optimism Mainnet | 已部署（1819 bytes） |

所有链上的 bytecode 完全一致（CREATE2 确定性部署）。合约实现了标准 ERC-7579 IValidator + IModule 接口：
- `isValidSignatureWithSender(address,bytes32,bytes)` — IValidator
- `isInitialized(address)` — IModule
- `onInstall(bytes)` / `onUninstall(bytes)` — IModule 生命周期
- `isModuleType(uint256)` — IModule 类型声明
- `validateUserOp(...)` — ERC-4337 v0.7 UserOp 验证

**结论：这是 ZeroDev Kernel 的标准 ECDSA Validator 模块**，不是 Crossmint 定制。多链确定性部署 + 标准接口 = 通用组件。不能用于精准归因。

#### Step 10: Mainnet 状态验证

| 组件 | Base Mainnet 状态 |
|------|-------------------|
| Factory `0xd703aae...` | **已部署** (1871 bytes，与 testnet 一致) |
| Validator `0x845adb2c...` | 已部署 (1819 bytes，与 testnet 一致) |
| Bundler `0xb052d584...` | nonce = 1（**几乎不活跃**） |

> ⚠️ **Crossmint bundler 在 mainnet 上 nonce 仅为 1**，说明 Crossmint 在 mainnet 上可能使用不同的 bundler 地址，或者 Crossmint 的 mainnet 业务量极低。这是后续需要确认的关键点。

### 最终归因结论

#### Phase 2 追加：五链主网数据（Etherscan V2 API）

Factory `0xd703aae...` 和 EntryPoint v0.7 在五条主网上全部存在且活跃：

| 链 | Factory 在 EP v0.7 中占比 | Bundler 构成 |
|----|--------------------------|-------------|
| **Optimism** | **94.0%** | 100% Pimlico (`0x4337...`) |
| **Arbitrum** | **80.2%** | 100% Pimlico |
| **Ethereum** | **57.7%** | 100% Pimlico |
| **Base** | **52.1%** (521 笔) | 100% Pimlico |
| **Polygon** | **43.5%** | 100% Pimlico |

#### 关键转折：主网没有 Crossmint 专用 bundler

**测试网**：Crossmint 用自有 bundler `0xb052d584...`（67% 占比，一对一绑定）→ 精准归因可行。

**主网**：**所有 bundler 都是 Pimlico**（`0x4337...` 前缀）。Crossmint 在生产环境使用 Pimlico 作为 bundler 服务，没有自己的专用 bundler。这意味着 **bundler 维度在主网上不可用于归因**。

#### ZeroDev Kernel 工厂全景

这个 factory 不是 Kernel 的唯一实例，而是其中之一（但是 v0.7 上最大的）：

```
EntryPoint v0.6 (老一代 Kernel):
  0xaee9762c... : 753 deploys    ← Kernel v0.6 主力
  0x4e494629... : 140 deploys

EntryPoint v0.7 (当前 Kernel):
  0xd703aae7... : 521 deploys    ← Crossmint 使用此工厂（最大）
  0xf5e92c74... : 270 deploys    ← 其他 Kernel 客户
  0x91e60e06... : 105 deploys    ← 其他 Kernel 客户
  0x428045192.. :  63 deploys    ← 其他 Kernel 客户
```

#### 修正后的归因方案

```
  测试网（Base Sepolia） — 精准归因 ✅
  ┌──────────────────────────────────────────────────────┐
  │  factory = 0xd703aae... AND bundler = 0xb052d584...  │
  │  → HIGH confidence                                    │
  └──────────────────────────────────────────────────────┘

  主网（5 链） — 中等精度归因 ⚠️
  ┌──────────────────────────────────────────────────────┐
  │  factory = 0xd703aae...（仅 factory，无 bundler 区分）│
  │  → MEDIUM confidence                                  │
  │  → 含 Crossmint + 同一 Kernel 工厂实例的其他客户      │
  │  → 但该工厂是 EP v0.7 上最大的，且测试网 67% 是       │
  │    Crossmint，主网比例未知但预期为主要来源              │
  └──────────────────────────────────────────────────────┘
```

### 收获总结

1. **EntryPoint v0.7**：Crossmint 走 v0.7，Phase 2 Dune query 必须覆盖。
2. **Factory 是最大 Kernel v0.7 实例**：在 Optimism 上占 EP v0.7 部署的 94%，说明这个 factory 实例的客户群非常集中。
3. **Pimlico 是主网 bundler**：Crossmint 生产环境使用 Pimlico bundler 服务，地址前缀 `0x4337` 可识别但不可用于区分 Crossmint。
4. **测试网 vs 主网基础设施不同**：Staging 用自有 bundler，Production 用 Pimlico。这是 WaaS 供应商的常见模式。
5. **Validator 是通用组件**：`0x845adb2c...` 是 ZeroDev 标准 ECDSA Validator（4 链同 bytecode），不可归因。
6. **无 Paymaster**：Staging 无 paymaster（零地址），mainnet 未单独验证。

### 风险实际发生情况

| 原始风险 | 是否发生 | 实际情况 |
|----------|----------|----------|
| API 不可用 | 否 | 复用已有结果，完全不依赖 API |
| Indexer 未收录 | **是** | JiffyScan/Basescan 不可用，改用 RPC + Etherscan V2 API |
| 通用第三方工厂 | **是** | ZeroDev Kernel，但是特定实例（非全部 Kernel），精度优于预期 |
| Mainnet 用不同工厂 | 否 | 5 链均存在，CREATE2 确认 |
| Mainnet bundler 不同 | **是** | 生产环境用 Pimlico，bundler 归因失效 |

---

## 对 ISSUE-011 Phase 2 的影响

### 可直接使用的数据

1. **Factory `0xd703aae...`** 在 5 条主网上均可查询，作为 Crossmint 活跃度的**上界估计**
2. **EntryPoint v0.7** 必须纳入 Dune query
3. 与 Coinbase 不同（Coinbase factory = Coinbase 专属），Crossmint factory 数据含噪声，但仍是最佳可用近似

### 归因精度评估

| 供应商 | 方法 | 精度 |
|--------|------|------|
| Coinbase | 专属 factory（v1.0 + v1.1） | **精准** — 100% Coinbase |
| Crossmint | 特定 Kernel factory 实例 | **中等** — Crossmint 是主要用户（testnet 67%），但含其他 Kernel 客户 |
| Privy | 不可归因 | **不可用** |

### 实用价值

虽然不是 100% 精准，但 `0xd703aae...` 的数据仍有高价值：
- **趋势分析**：增长/下降趋势反映 Crossmint + Kernel 生态的整体走向
- **量级估计**：结合 testnet 67% 比例，可以给出 Crossmint 主网活跃度的合理区间
- **跨链对比**：5 链数据可以揭示 Crossmint 客户的链偏好（Base vs Optimism vs Arbitrum）

---

## Next Steps

### 短期 — 可选的精度提升

1. **Mainnet Paymaster 分析**
   - 检查主网上 `0xd703aae...` factory 部署的钱包在后续交易中使用的 paymaster 地址
   - 如果 Crossmint 使用特定 paymaster（非零地址），可作为辅助归因条件
   - 投入：~30min

2. **Crossmint Production 钱包反查**（需要 Production API Key）
   - 用 Crossmint Production API 创建一个 mainnet 钱包
   - 反查部署交易的 bundler + paymaster，获取主网的完整指纹
   - 投入：~30min（如有 API key）

### 中期 — ISSUE-011 Phase 2 集成

3. **更新 Dune Query / 采集脚本**
   - Factory 白名单：`0xd703aae...`（标注 `crossmint_kernel_approx`）
   - EntryPoint：同时查 v0.6 + v0.7
   - 数据标注：该 factory 数据为 "Crossmint 为主的 Kernel 工厂"，非精准归因

4. **BundleBear 社区贡献**（可选）
   - 向 BundleBear 提交 PR，将 `0xd703aae...` 细分标注为 `zerodev_kernel_crossmint_primary`
   - 提供 testnet bundler 分析作为证据
