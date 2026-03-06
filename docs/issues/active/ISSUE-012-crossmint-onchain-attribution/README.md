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
- **Blocks**: ISSUE-011 Phase 2 Task 2-x（Crossmint 链上数据采集）— 结论：partial 归因可行

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
| EntryPoint | v0.7 (`0x0000000071727de22e5e9d8baf0edac6f37da032`) |
| Validator Module | `0x845adb2c711129d4f3966735ed98a9f09fc4ce57` |
| Paymaster | 无（零地址） |
| Bundler | `0xb052d58410a2c54e27d3d62f99bf8b2bb27a8d23` |
| 部署区块 | 38482363 |
| 部署 TX | `0x430bcd0add8d5b6ef10d2b46c68992c1fd77dc9f005a4dd82bdc5b9b5a2de379` |

### 方法

1. **Task 1 跳过**：复用 wallet-bench 已有测试结果（2026-03-05 运行），无需重新创建钱包
2. **Task 2**：通过 Base Sepolia RPC `eth_getLogs` 查询 EntryPoint v0.7 的 `AccountDeployed` 事件，以 sender = 测试钱包地址过滤，找到部署交易和 factory 地址
3. **Task 3**：在 BundleBear 工厂标签库中确认 `0xd703aae...` = `zerodev_kernel`；部署交易日志包含 `ModuleInstalled` 事件，确认 ERC-7579 模块化架构
4. **Task 4**：更新 `onchain-attribution.yaml`，Crossmint 从 `trackable: false` 升级为 `trackable: partial`

### 后续建议

- 验证 mainnet 是否使用相同 factory（CREATE2 确定性部署通常保持一致）
- 研究 Crossmint bundler 地址在 mainnet 上的唯一性，作为辅助归因条件
- 研究 validator module 地址是否为 Crossmint 定制，用于更精确的归因
