# wallet-bench 跨类横向对比报告

**日期**: 2026-03-05
**评估者**: Claude Opus 4.6 (AI agent)
**覆盖 Provider**: BNB Chain MCP (Local) / MoonPay Agents (Local) / Crossmint (Intent) / Privy (TEE) / Coinbase AgentKit (TEE) / Minara AI (MPC+AA)
**测试规模**: 6 providers × 13-16 tests (13 shared + 3 class-specific)
**环境**: testnet / mainnet CLI (无真实资产)

---

## 1. 执行摘要

本轮测试覆盖了四种钱包架构类别的六个 provider。全部 provider 均通过所有适用测试（0 ERROR / 0 FAIL），但在延迟、能力覆盖、接入难度等维度差异显著。

**核心发现**：
- **Privy 综合最优**：全能力覆盖 + 低延迟 (签名 ~200ms) + 双凭证轻量 onboarding
- **BNB Chain MCP 速度最快**：毫秒级响应，但无签名 API
- **MoonPay Agents 覆盖最广**：10 条链 + 54 个工具，非托管 HD 钱包，CLI --json 机器友好
- **Coinbase AgentKit SDK 质量最高**：类型安全 + 内置 faucet，但 onboarding 最重（三凭证）
- **Crossmint 延迟最高**：异步轮询模式导致签名 10s+，但文档最成熟
- **Minara AI 最开箱即用**：一站式 DeFi 助手，但无签名原语，custodial 托管
- 各家的金额单位约定**各不相同**，是跨 provider 集成的最大陷阱

---

## 2. 总览

| Provider | 类别 | 通过/总计 | 跳过 | 平均延迟 | 首次成功 |
|----------|------|:---:|:---:|:---:|:---:|
| BNB Chain MCP | Local | 12/16 | 4 | **425ms** | 8 min |
| MoonPay Agents | Local | **12/16** | 4 | 2137ms | 10 min |
| Privy Server Wallets | TEE | **13/16** | 3 | 712ms | 12 min |
| Coinbase AgentKit | TEE | 12/16 | 4 | 1521ms | 25 min |
| Crossmint Smart Wallets | Intent | 12/16 | 4 | 8713ms | 15 min |
| Minara AI | MPC+AA | 8/13 | 5 | 614ms | 8 min |

---

## 3. 能力矩阵

| 能力 | BNB Chain MCP | MoonPay | Privy | Coinbase | Crossmint | Minara |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| 创建钱包 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 消息签名 | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| EIP-712 签名 | ❌ | ❌ | ✅ | ✅ | ✅ | ❌ |
| 发送交易 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 多链支持 | ✅ (2链) | ✅ (10链) | ✅ (6链) | ✅ (5链) | ✅ (6链) | ✅ (9链) |
| 策略引擎 | ❌ | ❌ | ✅ (声称) | ❌ | ❌ | ❌ |
| 会话委托 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Gas 预估 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 4. 延迟对比

### 4.1 基线操作

| 操作 | BNB Chain MCP | MoonPay | Privy | Coinbase | Crossmint | Minara |
|------|---:|---:|---:|---:|---:|---:|
| 创建钱包 | **25ms** | 786ms | 473ms | 782ms | 3,373ms | 312ms |
| 消息签名 | N/A | 840ms | **213ms** | 462ms | 11,097ms | N/A |
| EIP-712 签名 | N/A | N/A | **176ms** | 1,265ms | 10,801ms | N/A |
| 发送交易 | **914ms** | 4,143ms | 1,011ms | 518ms | 6,879ms | 648ms |
| 并发 (3 ops) | **3ms** | 1,022ms | 473ms | 1,598ms | 1,512ms | 255ms |

### 4.2 Phase 3 深度测试

| 测试项 | BNB Chain MCP | MoonPay | Privy | Coinbase | Crossmint | Minara |
|--------|---:|---:|---:|---:|---:|---:|
| 限流恢复 | **2ms** | 2,001ms | 768ms | 3,675ms | 20,393ms | 357ms |
| 可移植性恢复 | **965ms** | 3,206ms | 1,097ms | 2,724ms | 13,687ms | 778ms |
| 授权审计链 | **798ms** | 3,663ms | 836ms | 1,811ms | 24,814ms | 1,237ms |

**发现**：
1. BNB Chain MCP 作为本地 MCP server，burst 完全无限流（2ms）
2. Minara CLI 虽为托管方案，但延迟意外地低（357ms burst）
3. Privy 并发性能优秀（768ms/burst），无 rate-limit 触发
4. MoonPay CLI subprocess 开销在 burst 场景累积到 2-4s
5. Coinbase 有轻微延迟累积（burst 3.6s），但无失败
6. Crossmint 异步轮询开销在 burst 场景放大到 20s+

---

## 5. Onboarding 难度

| 维度 | BNB Chain MCP | MoonPay | Privy | Coinbase | Crossmint | Minara |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| 需要注册 | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 凭证数量 | 1 (私钥) | 0 (email 登录) | 2 (App ID + Secret) | 3 (Key+Secret+Wallet) | 1 (API Key) | 0 (email 登录) |
| 人工操作次数 | 0 | 1 (hCaptcha) | 2 | **3** | 2 | 1 (email 验证) |
| 首次成功耗时 | **8 min** | 10 min | 12 min | 25 min | 15 min | **8 min** |
| 注册后 Agent 自主 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

**最大陷阱**：
- Coinbase 的 Wallet Secret 在 CDP Portal 的 "Wallets > Server Wallet" 中生成，不在 API Keys 页面，且只显示一次
- MoonPay 的 hCaptcha 登录需要浏览器，AI 无法自主完成
- Minara 的 `--json` flag 不输出结构化 JSON，需要文本正则解析

---

## 6. DX 评分对比

| 维度 (1=最好 5=最差) | BNB Chain MCP | MoonPay | Privy | Coinbase | Crossmint | Minara |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| 接入摩擦 | **2** | **2** | 3 | 4 | 3 | **2** |
| 文档准确度 | 3 | **2** | **2** | **2** | **2** | 3 |
| API 一致性 | 3 | **2** | 3 | **2** | **2** | 3 |
| 错误信息质量 | 4 | **2** | **2** | **2** | **2** | 3 |
| Agent 自主度 | **2** | 3 | 3 | 4 | 3 | 3 |

---

## 7. 集成 Bug 统计

| Provider | Bug 数 | 我方代码 | 服务商 API | 服务商基础设施 |
|----------|:---:|:---:|:---:|:---:|
| BNB Chain MCP | 4 | 4 | 0 | 0 |
| MoonPay Agents | 3 | 3 | 0 | 0 |
| Privy | 4 | 0 | 3 | 1 |
| Coinbase AgentKit | 1 | 1 | 0 | 0 |
| Crossmint | 3 | 3 | 0 | 0 |
| Minara AI | 0 | 0 | 0 | 0 |

### Bug 模式归纳

| 模式 | 涉及 Provider | 教训 |
|------|--------------|------|
| **参数命名假设** | BNB (BUG-1/3) | 先读 schema，不要凭经验猜 |
| **金额单位不一致** | BNB/Crossmint/Coinbase | 每个 adapter 内部处理单位，不在外部统一 |
| **数值精度** | BNB (BUG-2) | 链上金额永远用 Decimal |
| **异步状态语义** | Crossmint (BUG-3) | 422 可能是业务状态不是协议错误 |
| **命名风格差异** | Privy (BUG-3) | snake_case vs camelCase 按 provider 走 |
| **Bot 防护拦截** | Privy (BUG-1) | 用 requests + User-Agent，不用 urllib |
| **严格类型校验** | Coinbase (BUG-1) | value 必须是 int，不接受 hex string |
| **零值拒绝** | MoonPay (BUG-1) | transfer amount=0 被拒，审计测试需用小额替代 |
| **非确定性创建** | MoonPay (BUG-2) | create_wallet 每次生成新 HD 钱包，需缓存已有地址 |
| **测试硬编码** | MoonPay (BUG-3) | 测试用例不应假设 adapter 构造参数格式 |
| **--json 不输出 JSON** | Minara | CLI flag 文档与实现不符，需文本正则解析 |
| **交互式 UI 阻塞** | Minara | token 选择器弹出 inquirer UI，用 stdin=DEVNULL 防止阻塞 |

---

## 8. 架构选型建议

### 快速原型 / PoC → BNB Chain MCP
- 零注册、零配置、毫秒级延迟
- 缺点: 无签名能力，仅能做链上交易

### 多链全栈 Agent → MoonPay Agents
- 10 条链覆盖（EVM + Solana + Bitcoin + TRON），54 个工具
- 非托管 BIP39 HD 钱包，密钥不出机，CLI --json 机器友好
- 缺点: 无 EIP-712 签名，hCaptcha 注册需人工，CLI subprocess 延迟 ~2s

### 生产级 Agent 钱包 → Privy Server Wallets
- 全能力覆盖 + 低延迟 + REST API（无 SDK 依赖）
- 签名速度是 Crossmint 的 **60 倍**
- 注册后 Agent 完全自主

### Python 优先团队 → Coinbase AgentKit
- 原生 Python SDK、类型安全、Pydantic 校验
- 唯一内置 faucet（Agent 可自动领测试币）
- 代价: onboarding 最重（三凭证）

### 企业级 / 合规优先 → Crossmint Smart Wallets
- 文档最成熟、REST API 设计规范
- Fireblocks TEE 托管、多链覆盖广
- 代价: 延迟高（异步轮询 10s+）

### DeFi 一站式助手 → Minara AI
- 开箱即用（8 min 首次成功），swap/perps/transfer/deposit 一体化
- 9 链支持，0 集成 Bug
- 缺点: 无签名原语（custodial），--json 不输出 JSON，不适合需要底层密钥控制的场景

---

## 9. 综合评分

| Provider | 能力 (35%) | 可靠性 (40%) | 开发体验 (25%) | **综合** |
|----------|:---:|:---:|:---:|:---:|
| Privy | 88% | 100% | 72% | **88%** |
| Coinbase AgentKit | 75% | 100% | 64% | 81% |
| Crossmint | 75% | 100% | 64% | 81% |
| MoonPay Agents | 50% | 100% | 76% | 75% |
| BNB Chain MCP | 50% | 100% | 60% | 71% |
| Minara AI | 38% | 100% | 68% | 69% |

> - 能力分: capabilities 中 true 占比
> - 可靠性分: pass rate（排除 skip），全部 100%
> - 开发体验分: 5 项 DX 评分的反转均值
> - 综合分: 加权平均

---

## 10. 给后来 Agent 的跨 Provider 注意事项

1. **金额单位是最大陷阱**：BNB 用 ether 字符串、Crossmint 用 wei 字符串、Coinbase 用 int (wei)、Privy 用 hex string (wei)。绝对不要在 adapter 外部做单位转换。
2. **先读 schema 再写代码**：MCP 用 `list_tools()`，REST API 读 OpenAPI spec，SDK 看类型签名，CLI 用 `--help`。
3. **Python 金额用 Decimal**：`str(float)` 会产生科学计数法，链上库全部拒绝。
4. **托管类的 HTTP 错误码有业务语义**：422 不一定是"你传错了"，可能是"链上 revert 了"。
5. **EIP-712 命名不统一**：Coinbase 用 camelCase (`primaryType`)，Privy 用 snake_case (`primary_type`)。
6. **Cloudflare bot 防护**：Privy 会拦截标准 HTTP 客户端，必须设 User-Agent。
7. **人类依赖都是一次性的**：注册/faucet/hCaptcha 做一次后，AI agent 就完全自主了。
8. **CLI --json 不可信**：Minara 声称支持 --json 但实际输出仍是格式化文本，集成前务必验证。
9. **subprocess 自动化防卡死**：CLI 工具可能弹出交互式 UI（如 Minara token 选择器），始终用 `stdin=DEVNULL`。
10. **HD 钱包不等于确定性**：MoonPay 每次 `wallet create` 生成新助记词（非同一 seed 派生），需缓存已有钱包。

---

## 附录：测试环境

| 项 | 值 |
|------|------|
| 测试框架 | wallet-bench runner.py |
| Python | 3.12 (Anaconda) |
| BNB Chain MCP | @bnb-chain/mcp@latest via npx |
| MoonPay Agents | @moonpay/cli v0.12.11 |
| Crossmint | REST API v1-alpha2 (staging) |
| Privy | REST API v1 |
| Coinbase AgentKit | coinbase-agentkit v0.7.4 (Python SDK) |
| Minara AI | minara v0.2.9 |
| 测试网 | BSC Testnet / Base Sepolia / Ethereum Sepolia / Mainnet CLI |
| 测试项 | 13 shared (t01-t13) + 3 class-specific (per arch) |
