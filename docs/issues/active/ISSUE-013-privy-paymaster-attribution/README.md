---
title: 'ISSUE-013: Privy 链上归因突破 — Paymaster / Bundler / EIP-7702 足迹调研'
concepts:
- on-chain-analytics
- competitive-intelligence
- erc-4337
- eip-7702
---
# ISSUE-013: Privy 链上归因突破 — Paymaster / Bundler 足迹调研

## Meta
- **Status**: CLOSED (confirmed not trackable — deterministic attribution infeasible; probabilistic attribution not worth pursuing)
- **Priority**: P2
- **Component**: scripts/, docs/issues/active/ISSUE-011-competitor-monitoring/
- **Owner**: —
- **Date**: 2026-03-06
- **Effort**: Short—completed 2026-03-06
- **Blocks**: ~~ISSUE-011 Phase 2 Task 2-x~~ — Privy 确认链上不可追踪，不阻塞 Phase 2

## 结论（Final Conclusion）

**确认 Privy 链上确定性归因不可行，概率归因投入产出比过低，不建议继续投入。**

### 路径一：ERC-4337 Smart Wallet（确定性归因 ❌）

1. **Smart Wallet 路径**：bundlerUrl/paymasterUrl 由开发者在 Privy Dashboard 自行配置（Pimlico/ZeroDev/Alchemy/Biconomy/Coinbase），无统一 Privy 专属地址。默认 Bundler 为公共 Pimlico。
2. **SDK 源码**：`@privy-io/react-auth@3.16.0` 内嵌 5 家 provider 域名检测逻辑，但不含任何硬编码 paymaster 合约地址。
3. **Go SDK 测试地址** `0x2cc0c798...` 经验证为 Alchemy Verifying Paymaster（Sepolia 测试网），非生产、非 Privy 专属。
4. **wallet-bench adapter**：`adapters/privy.py` 走 REST API + `eth_sendTransaction`，不走 ERC-4337 UserOp，无 paymaster 足迹。

### 路径二：EIP-7702 Native Gas Sponsorship（确定性归因 ❌ / 概率归因 ⚠️ 不推荐）

1. **Privy Native Gas Sponsorship 确认使用 EIP-7702** — 2025-09-24 正式上线，支持 15+ 主网（Ethereum/Base/Optimism/Arbitrum/Polygon/BNB/Unichain 等）。
2. **链上可检测**：`eth_getCode(EOA)` 返回 `0xef0100` + 20 字节 impl 地址（EIP-7702 delegation designator）。
3. **默认 impl 为 ZeroDev Kernel**（`KERNEL_V3_3`），可选 Biconomy Nexus (`0x000000004F43C49e93C970E84001853a70923B03`)、Pimlico SimpleAccount 等。
4. **核心归因障碍**：同一 impl 地址被 Privy 用户和直接 SDK 用户（ZeroDev/Biconomy/Alchemy 直接集成方）共享。**字节码完全一致，链上不可区分**。
5. **BundleBear 已全面追踪 EIP-7702**（8 链覆盖），但 label 系统中**无 "Privy" 条目** — Privy 签名发生在链下，链上只能看到 authorized contract（ZeroDev/Biconomy 等），看不到是谁提供的签名服务。
6. **ZeroDev 30.2 万 7702 账户 ≠ Privy 用户** — ZeroDev 被 Privy + 直接 SDK 用户 + 其他集成方共享。

### 概率归因 5 条路径评估结果

| 路径 | 评估 | 最终判断 |
|------|------|---------|
| 路径1: EIP-7702 字节码指纹（impl 地址匹配） | impl 地址被多家共享（ZeroDev 30万+账户不全是 Privy） | **不可行** — 噪声太大 |
| 路径2: Sponsorship 聚类（paymaster 地址） | paymaster 被多 app 共享，无法区分 Privy 与直接集成 | **极弱** — 无法区分 |
| 路径3: Factory + Fresh EOA 启发式 | EIP-7702 不需要 factory，EOA 保持原地址 | **不适用** |
| 路径4: SDK calldata 指纹 | 签名在链下完成，calldata 无 Privy 特征 | **不可行** |
| 路径5: 离链辅助（向 Privy/Biconomy 申请数据） | 唯一靠谱路径，但不属于技术归因范畴 | **唯一可行方向，非自动化** |

### 最终建议

- 接受 Privy 链上不可追踪（确定性归因和概率归因均不可行）
- 不建议创建 ISSUE-013B（概率归因试点），投入产出比过低
- 将精力转移到 Crossmint 工厂反查（ISSUE-012）和 Phase 2 其他可追踪供应商
- **意外收获**：EIP-7702 调研发现其他竞品（Coinbase/MetaMask/TrustWallet/Bitget/Ambire）有专属 7702 impl 合约，可直接追踪


## Background

ISSUE-011 Task 0-3 调研结论：Privy 不部署自有工厂合约，而是作为中间层让开发者在 Dashboard 中选择底层 Smart Wallet 实现（Coinbase Smart Wallet / ZeroDev Kernel / Alchemy Light Account / Safe / Biconomy / Thirdweb）。这意味着 Privy 创建的钱包在链上归因到底层工厂，无法与"直接使用底层 SDK"的钱包区分。

**核心问题**：Privy npm 周下载量 337k，是 6 家中最大的竞品，但链上追踪是盲区。

**新的追踪思路**：Privy 虽然不控制工厂合约，但可能在以下环节留有可识别的链上足迹：
1. **Paymaster**：Privy 的 Gas Sponsorship 功能使用专属 Paymaster → 通过 Paymaster 地址归因
2. **Bundler**：Privy 可能运营或合作专属 Bundler → 通过 Bundler URL/地址归因
3. **callData 特征**：Privy SDK 在构造 UserOp 时可能附加特定的 callData 前缀或结构

## 目标

1. 调研 Privy 的 Gas Sponsorship / Paymaster 实现，找到具体 Paymaster 地址
2. 调研 Privy 是否运营专属 Bundler 或与特定 Bundler 合作（Pimlico / Alto / 自建）
3. 通过 wallet-bench 的 Privy adapter 创建测试钱包，链上查看 UserOp 中的 paymaster + bundler
4. 如找到可归因字段，更新 `onchain-attribution.yaml`
5. 产出追踪方案建议：可行 / 部分可行 / 确认不可行

## 任务分解

### Task 1: Privy 文档 + SDK 源码调研（~2h）

**调研目标 A — Paymaster**：
- 查阅 https://docs.privy.io/wallets/using-wallets/evm-smart-wallets/gas
- 搜索关键词：`paymaster`、`gas sponsorship`、`pimlico`、`paymaster address`
- 查阅 `@privy-io/server-auth` npm 包源码（https://registry.npmjs.org/@privy-io/server-auth）
- 查阅 https://github.com/privy-io/privy-js（如果公开）
- 重点：找到任何硬编码的 paymaster 地址或 paymaster API 端点

**调研目标 B — Bundler**：
- 查阅 https://docs.privy.io（搜索 `bundler`、`userop`、`alto`）
- 看 Privy 是否有公开的 Bundler URL（如 `bundler.privy.io`）
- 查阅 Privy 的技术博客 / changelog（https://changelog.privy.io）

**交付物**：文档调研结论 + 找到的任何 paymaster/bundler 地址或 URL

---

### Task 2: 通过 wallet-bench 测试钱包链上验证（~1h）

**前提**：Task 1 找到了 paymaster 或 bundler 的候选信息

**步骤**：
```bash
python runner.py run --provider privy --config config.yaml
```
- 记录创建的钱包地址（Ethereum Sepolia）
- 在 JiffyScan 查询该钱包的 UserOp：
  ```
  https://jiffyscan.xyz/account/{wallet_address}?network=sepolia
  ```
- 对比 UserOp 中的 `paymaster` 和 `entryPointSender`（bundler）字段与 Task 1 调研结果

**注意**：Privy 测试网可能不启用 Gas Sponsorship（需要付费功能），此时 UserOp 中 paymaster 为空地址 `0x000...000`。需要检查 Privy Dashboard 是否可以开启 Staging 环境的 gas sponsorship。

**备用方案**：如果自测无法开启 sponsorship，搜索已知使用 Privy 的公开 DApp（如 Privy 官网 demo、Friend.tech 等已知集成方），查询其用户的 UserOp。

**交付物**：实际 UserOp 中的 paymaster 地址 + bundler 信息

---

### Task 3: 归因可行性判断（~1h）

根据 Task 1 + Task 2 的结果，判断以下场景：

**场景 A — 找到 Privy 专属 Paymaster 地址**：
- 可行性：高
- 追踪方式：通过 Dune / BundleBear 查询使用该 Paymaster 的所有 UserOp → 按月统计 unique sender 数
- 置信度：中（不是所有 Privy 用户都会开启 gas sponsorship）
- 在 `onchain-attribution.yaml` 中记录为 `trackable: partial`，注明通过 paymaster 归因

**场景 B — 找到 Privy 专属 Bundler URL**：
- 可行性：中
- Bundler URL 不直接暴露在链上（它是 RPC 端点），但有些 bundler 会在 UserOp 的 beneficiary 字段留地址
- 需要进一步验证 beneficiary 是否可识别

**场景 C — UserOp 结构有特定前缀/签名特征**：
- 可行性：低（需要深入 callData 解析，且容易被 SDK 更新破坏）

**场景 D — 完全无可识别足迹**：
- 结论：确认 Privy 链上追踪不可行
- 在 `onchain-attribution.yaml` 中更新 reason，给出详细的调研过程记录
- 建议 ISSUE-011 Dashboard 保持"Privy 链上不可追踪"标注，不再投入时间

---

### Task 4: 更新 onchain-attribution.yaml（~30min）

无论结论如何，更新 `onchain-attribution.yaml` 中 Privy 条目，补充本次调研结果：

```yaml
privy:
  trackable: false  # 或 partial
  # 如果找到 paymaster：
  paymaster_attribution:
    possible: true
    paymaster_address: "0x..."
    source: "..."
    caveat: "仅覆盖开启 gas sponsorship 的 Privy 用户，非全量"
  # 如果完全无法追踪：
  investigation_log:
    - date: "2026-03-06"
      finding: "文档无 paymaster 地址，SDK 源码无硬编码地址，测试 UserOp paymaster 为零地址"
      conclusion: "确认链上无可识别足迹，不投入更多时间"
```

---

## EIP-7702 调研详情（2026-03-06 追加）

### EIP-7702 链上现状

| 指标 | 数值 | 来源 |
|------|------|------|
| 全链累计 authorization 总数（2025全年） | 9,100 万 | BundleBear 年度报告 |
| 期末存活有效 delegation EOA | 660 万（含 265 万黑客合约） | BundleBear |
| 合法账户 | ~400 万 | BundleBear |
| 月活峰值（2025.12） | 150 万 | BundleBear |
| 7702 × 4337 UserOps 账户 | 80.5 万 | BundleBear |

### 主要 EIP-7702 Implementation Contract 排名（BundleBear 数据）

| 排名 | 合约 | Live 账户数 | 可追踪？ |
|------|------|-----------|---------|
| 1 | Crime（黑客合约） | 2,681,807 | — |
| 2 | Bitget | 868,757 | ✅ 专属 impl |
| 3 | MetaMask Delegator | 698,086 | ✅ 专属 impl |
| 4 | TokenPocket | 586,797 | ✅ 专属 impl |
| 5 | Simple 7702Account | 527,903 | ✅ 专属 impl |
| 6 | Ambire | 508,123 | ✅ 专属 impl |
| 7 | **Coinbase Wallet** | 506,358 | ✅ 专属 impl `0x7702cb55...` |
| 8 | TrustWallet | 347,087 | ✅ 专属 impl |
| 9 | **ZeroDev** | 302,218 | ⚠️ 被多家共享（含 Privy） |
| 10 | **Alchemy** | 285,328 | ⚠️ 被多家共享 |
| ... | **Biconomy Nexus**（5个地址） | ~54,000 | ⚠️ 被多家共享 |

### Privy 在 EIP-7702 中的角色

Privy 是**签名基础设施层**，提供：
- `useSign7702Authorization` SDK hook（React/React Native/Node）
- `eth_sign7702Authorization` REST API
- `signAuthorization` 向任意 implementation contract 委托

**Privy 本身不部署 authorized contract** — delegation 目标取决于 app 集成选择（ZeroDev/Biconomy/Alchemy 等）。签名在链下完成，链上只能看到 authorized contract，看不到是谁提供的签名服务。

### BundleBear EIP-7702 数据体系

BundleBear（by 0xKofi）已建立完整的 EIP-7702 独立追踪系统：

```
models/eip7702/
├── labels/
│   ├── eip7702_labels_authorized_contracts.sql  ← 合约标签
│   └── eip7702_labels_apps.sql                  ← 应用标签
├── authorizations/  ← 8链独立授权数据表
├── actions/         ← 8链行为数据表
├── metrics/         ← 指标聚合（含 7702×4337 overlap）
└── state/           ← EOA 状态快照
```

**关键发现：`eip7702_labels_authorized_contracts.sql` 中无 "Privy" 条目。**

### Dune 社区 EIP-7702 Dashboard

| Dashboard | 作者 | URL |
|-----------|------|-----|
| EIP-7702 | @wintermute_research | https://dune.com/wintermute_research/eip7702 |
| EIP-7702 Adoption | @0xkhmer | https://dune.com/0xkhmer/eip-7702 |
| Transaction Type Adoption EIP-7702 Type4 | @lorenz234 | https://dune.com/lorenz234/transaction-type-adoption |
| Daily TrustWallet EIP-7702 Delegation | — | https://dune.com/queries/6356693/10112559 |

### 对 ISSUE-011 的意外收获

虽然 Privy 不可追踪，但调研发现以下竞品有**专属 EIP-7702 impl 合约**，可直接归因：

| 竞品 | 7702 Impl 地址 | Live 账户数 |
|------|---------------|-----------|
| **Coinbase Wallet** | `0x7702cb554e6bfb442cb743a7df23154544a7176c` | 506,358 |
| MetaMask Delegator | `0x63c0c19a282a1b52b07dd5a65b58948a07dae32b` | 698,086 |
| TrustWallet | `0xd2e28229f6f2c235e57de2ebc727025a1d0530fb` | 347,087 |
| Bitget | `0xa845c74344fc9405b1fcf712f04668979573c1bf` | 868,757 |
| Ambire | `0x5a7fc11397e9a8ad41bf10bf13f22b0a63f96f6d` | 508,123 |

> Coinbase Wallet 的 7702 数据（50.6 万账户）可纳入 ISSUE-011 Phase 2 链上采集，
> 与现有 ERC-4337 factory 数据互补。


## 备用方案：放弃链上追踪，改用"Privy 生态声誉指标"

如果所有链上路径均失败，可考虑以下替代代理指标：

| 指标 | 数据源 | 获取难度 | 置信度 |
|------|--------|---------|--------|
| Privy.io 官网流量趋势 | SimilarWeb（有免费额度）或 PublicWWW | 中 | 低 |
| "Built with Privy" 生态目录 | https://www.privy.io/customers | 低（手动） | 中 |
| Privy 博客/Changelog 更新频率 | https://changelog.privy.io | 低（已有 docs 密度指标） | 低 |
| Privy 在已知 DApp 的集成数 | DApp Radar / 手工整理 | 高（手动维护） | 中 |

**结论建议**：如果 paymaster 路径失败，接受 Privy 链上不可追踪，将精力转移到 Crossmint（ISSUE-012）的反查上。

---

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Privy gas sponsorship 在 Staging 不可用 | 测试 UserOp 的 paymaster 为空 | 查找已知使用 Privy 的公开 DApp 的 UserOp |
| Privy 使用 Pimlico 等公共 paymaster | paymaster 归因不唯一 | 标注为不可追踪，说明理由 |
| SDK 源码未公开 | 无法找到硬编码地址 | 依赖文档和链上反查 |

## 成功标准

- [x] 完成 Privy docs + SDK 源码关于 paymaster/bundler 的完整调研
- [x] ~~通过 wallet-bench Privy adapter 创建测试钱包并查询链上 UserOp~~ — 取消，文档 + SDK 调研已得出确定结论，无需实测验证
- [x] `onchain-attribution.yaml` 中 Privy 条目有明确结论（确认不可行 + 详细调研记录）
- [x] 不可追踪，无需 Dune/BundleBear query 方案
- [x] EIP-7702 路径完整评估（5 条概率归因路径 + BundleBear 7702 数据交叉验证）
