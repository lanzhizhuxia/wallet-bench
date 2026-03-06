---
title: 'ISSUE-013: Privy 链上归因突破 — Paymaster / Bundler 足迹调研'
concepts:
- on-chain-analytics
- competitive-intelligence
- erc-4337
---
# ISSUE-013: Privy 链上归因突破 — Paymaster / Bundler 足迹调研

## Meta
- **Status**: CLOSED (confirmed not trackable)
- **Priority**: P2
- **Component**: scripts/, docs/issues/active/ISSUE-011-competitor-monitoring/
- **Owner**: —
- **Date**: 2026-03-06
- **Effort**: Short—completed 2026-03-06
- **Blocks**: ~~ISSUE-011 Phase 2 Task 2-x~~ — Privy 确认链上不可追踪，不阻塞 Phase 2

## 结论（Final Conclusion）

**确认 Privy 链上归因不可行。**两条路径均失败：

1. **Smart Wallet 路径**：bundlerUrl/paymasterUrl 由开发者在 Privy Dashboard 自行配置（Pimlico/ZeroDev/Alchemy/Biconomy/Coinbase），无统一 Privy 专属地址。默认 Bundler 为公共 Pimlico。
2. **Native Gas Sponsorship（EIP-7702）**：Privy 后端处理 paymaster，但文档仅提及 "Paymasters partnered with Privy"，未公开合约地址。
3. **SDK 源码**：`@privy-io/react-auth@3.16.0` 内嵌 5 家 provider 域名检测逻辑，但不含任何硬编码 paymaster 合约地址。
4. **Go SDK 测试地址** `0x2cc0c798...` 经验证为 Alchemy Verifying Paymaster（Sepolia 测试网），非生产、非 Privy 专属。
5. **wallet-bench adapter**：`adapters/privy.py` 走 REST API + `eth_sendTransaction`，不走 ERC-4337 UserOp，无 paymaster 足迹。

调研结果已写入 `onchain-attribution.yaml` 中 Privy 条目的 `investigation_log`。

**建议**：接受 Privy 链上不可追踪，将精力转移到 Crossmint 工厂反查（ISSUE-012）。


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
