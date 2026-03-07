# wallet-bench

AI Agent 钱包服务横向对比测试平台 — 覆盖 WaaS 基础设施供应商与 OpenClaw 生态 Agent Skills。自动化测试密钥管理、签名、交易、治理、稳定性及 DeFi 能力。

## 评测对象

### WaaS 基础设施供应商（7 家）

| 供应商 | `--provider` 参数值 | 架构类型 | 测试网链 |
|--------|---------------------|---------|----------|
| BNB Chain MCP | `bnbchain_mcp` | local | BSC testnet |
| Crossmint Smart Wallets | `crossmint` | intent | Base Sepolia, Ethereum Sepolia, Polygon Amoy |
| Coinbase AgentKit (CDP) | `coinbase_agentkit` | intent | Base Sepolia |
| Privy | `privy` | delegated | Ethereum Sepolia |
| MoonPay | `moonpay` | delegated | Ethereum |
| Minara | `minara` | custodial | Base |
| OKX OnchainOS | `okx_onchainos` | intent | — |

### OpenClaw 生态 Agent Skills（5 家）

| 供应商 | `--provider` 参数值 | 架构类型 | 测试网链 |
|--------|---------------------|---------|----------|
| Clawlett | `clawlett` | smart_account | Base (主网) |
| Para Wallet | `para_wallet` | mpc | Ethereum, Solana, Cosmos |
| Universal Trading | `universal_trading` | local | BSC, ETH, Solana 等 |
| Polymarket Agent | `polymarket_agent` | local | Polygon (主网) |
| Coinpilot Hyperliquid | `coinpilot_hyperliquid` | intent | Hyperliquid L1 |

> 以上 5 家来自 [OpenClaw ClawHub](https://github.com/openclaw/skills) 生态，是 Agent 技能插件而非独立钱包服务商。它们封装了底层钱包/交易能力，供 AI Agent 调用。

## 前置要求

- **Python >= 3.10**
- **Node.js >= 18**（BNB Chain MCP 需要 `npx`；MoonPay / Minara 需要 `npm`）

## 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/<your-org>/wallet-bench.git
cd wallet-bench

# 2. 安装 Python 依赖
pip install -e .

# 3. 复制配置模板并填入凭证（只需填你想测的那个供应商即可）
cp config.example.yaml config.yaml

# 4. 运行单个供应商测试
python runner.py run --provider crossmint --config config.yaml

# 5. 多次运行取中位数延迟
python runner.py run --provider crossmint --config config.yaml --runs 3
```

> **不想跑测试，只想看 Dashboard？** 项目自带示例数据，直接打开即可：
> ```bash
> open web/index.html
> ```

## 配置说明

所有凭证存放在 `config.yaml`（已 gitignore）。从 `config.example.yaml` 复制后，**只需填你想测的那个供应商**，其他的留着占位符不影响运行。

> **安全机制**：Runner 内置网络白名单，仅允许测试网链，主网 chain ID 默认被拦截。

---

### BNB Chain MCP

通过 MCP stdio 协议调用 BNB Chain 服务器，需要安装 Node.js（用于 `npx`）。

|  |  |
|--|--|
| GitHub | https://github.com/bnb-chain/bnb-chain-mcp |
| npm 包 | `@bnb-chain/mcp` |
| 文档 | https://github.com/bnb-chain/bnb-chain-mcp#readme |
| 集成方式 | MCP Server (stdio) |

| 配置项 | 说明 |
|--------|------|
| `private_key` | BSC 测试网私钥（`0x` 开头的 hex） |
| `network` | 网络名称，默认 `bsc-testnet` |

**获取测试币 tBNB**：https://www.bnbchain.org/en/testnet-faucet

```yaml
providers:
  bnbchain_mcp:
    private_key: "0xYOUR_BSC_TESTNET_PRIVATE_KEY"
    network: bsc-testnet
```

---

### Crossmint Smart Wallets

REST API 适配器，使用 Crossmint Staging 环境。需要一个 EOA 私钥用于批准签名/交易请求。

|  |  |
|--|--|
| 官网 | https://www.crossmint.com |
| GitHub (MCP) | https://github.com/Crossmint/mcp-crossmint-checkout |
| 文档 | https://docs.crossmint.com/wallets/smart-wallets/overview |
| 集成方式 | REST API / MCP Server (stdio) |

| 配置项 | 说明 |
|--------|------|
| `api_key` | Crossmint Staging API Key（`sk_staging_...`） |
| `chain` | 目标链，如 `base-sepolia` |
| `eoa_private_key` | 用于审批签名的 EOA 私钥（`0x` 开头的 hex） |

**获取 API Key**：https://staging.crossmint.com/console → API Keys

```yaml
providers:
  crossmint:
    api_key: "sk_staging_YOUR_KEY"
    chain: base-sepolia
    eoa_private_key: "0xYOUR_EOA_PRIVATE_KEY"
```

---

### Coinbase AgentKit (CDP)

使用 Coinbase Developer Platform SDK，需要两个凭证文件。

|  |  |
|--|--|
| GitHub | https://github.com/coinbase/agentkit |
| PyPI 包 | `coinbase-agentkit` |
| 文档 | https://docs.cdp.coinbase.com/agentkit/docs/welcome |
| 集成方式 | Python SDK |

| 配置项 | 说明 |
|--------|------|
| `cdp_key_file` | CDP API Key JSON 文件路径 |
| `wallet_secret` | CDP 钱包密钥（base64 编码的 EC P-256 DER 密钥） |
| `network_id` | 网络 ID，默认 `base-sepolia` |

**获取凭证**：https://portal.cdp.coinbase.com → API Keys

1. 创建 API Key 并下载 JSON 文件 → 保存为项目根目录的 `cdp_api_key.json`
2. 导出钱包密钥 → 保存为 `cdp_wallet_secret.txt` 或直接粘贴到 config

```json
// cdp_api_key.json
{
  "id": "your-key-id",
  "privateKey": "your-ed25519-private-key-base64"
}
```

```yaml
providers:
  coinbase_agentkit:
    cdp_key_file: "cdp_api_key.json"
    wallet_secret: "MIGHAgEA..."
    network_id: base-sepolia
```

---

### Privy

服务端钱包 API，需要 Privy 应用凭证。

|  |  |
|--|--|
| GitHub (MCP) | https://github.com/privy-io/privy-mcp-server |
| npm 包 | `@privy-io/mcp-server` |
| 文档 | https://docs.privy.io/guide/server-wallets |
| 集成方式 | REST API / MCP Server (stdio) |

| 配置项 | 说明 |
|--------|------|
| `app_id` | Privy 应用 ID |
| `app_secret` | Privy 应用密钥（`privy_app_secret_...`） |
| `chain` | 目标链，如 `ethereum-sepolia` |
| `wallet_id` | （可选）预充值的钱包 ID，留空则自动创建新钱包 |

**获取凭证**：https://dashboard.privy.io → Settings → API Keys

```yaml
providers:
  privy:
    app_id: "YOUR_APP_ID"
    app_secret: "privy_app_secret_YOUR_SECRET"
    chain: ethereum-sepolia
    wallet_id: ""
```

---

### MoonPay

基于 CLI 的适配器，需要安装 MoonPay CLI 工具。

|  |  |
|--|--|
| 官网 | https://www.moonpay.com |
| npm 包 | `@moonpay/cli` |
| 文档 | https://docs.moonpay.com |
| 集成方式 | CLI / MCP Server (`mp mcp`) |

| 配置项 | 说明 |
|--------|------|
| `wallet_name` | 钱包名称，默认 `bench` |
| `chain` | 链名称，默认 `ethereum` |

**安装与登录**：
```bash
npm install -g @moonpay/cli
mp auth login
```

```yaml
providers:
  moonpay:
    wallet_name: bench
    chain: ethereum
```

---

### Minara

基于 CLI 的适配器，需要安装 Minara CLI 工具。

|  |  |
|--|--|
| GitHub | https://github.com/Minara-AI/skills |
| npm 包 | `minara` |
| 集成方式 | CLI |

| 配置项 | 说明 |
|--------|------|
| `chain` | 链名称，默认 `base` |

**安装与登录**：
```bash
npm install -g minara
minara auth login
```

```yaml
providers:
  minara:
    chain: base
```

---

## 凭证文件一览

| 文件 | 用途 | 已 gitignore |
|------|------|:------------:|
| `config.yaml` | 所有供应商凭证及安全设置 | Yes |
| `.env` | 可选的环境变量 | Yes |
| `cdp_api_key.json` | Coinbase CDP API Key（id + privateKey） | Yes |
| `cdp_wallet_secret.txt` | Coinbase CDP 钱包密钥（base64） | Yes |

## 项目结构

```
wallet-bench/
├── adapters/                  # 供应商适配器
│   ├── base.py                #   共享基类与数据模型
│   ├── bnbchain_mcp.py        #   BNB Chain (MCP stdio)
│   ├── crossmint.py           #   Crossmint Smart Wallets (REST API)
│   ├── coinbase_agentkit.py   #   Coinbase AgentKit (CDP SDK)
│   ├── privy.py               #   Privy (REST API)
│   ├── moonpay.py             #   MoonPay (CLI)
│   ├── minara.py              #   Minara (CLI)
│   ├── okx_onchainos.py       #   OKX OnchainOS (REST API)
│   ├── clawlett.py            #   Clawlett (Gnosis Safe + Zodiac)
│   ├── para_wallet.py         #   Para Wallet (MPC REST API)
│   ├── universal_trading.py   #   Universal Trading (Particle Network)
│   ├── polymarket_agent.py    #   Polymarket Agent (CLI)
│   └── coinpilot_hyperliquid.py #  Coinpilot Hyperliquid (CLI)
├── cases/                     # 测试用例（所有供应商共用）
├── evaluations/               # 各供应商 DX 评估 (YAML)
├── providers/                 # 供应商元数据 (YAML)
├── docs/
│   ├── methodology/
│   │   ├── test-design-philosophy.md  # 测试设计思路：为什么选这些测试
│   │   └── test-item-reference.md     # 测试项详解：每个测试做什么、怎么判定
│   └── next-steps.md                  # 候选评测对象与未来方向
├── scripts/                   # 构建脚本
├── web/                       # 静态 Dashboard (HTML/CSS/JS)
├── runner.py                  # 测试编排 CLI
├── config.example.yaml        # 配置模板
└── config.yaml                # 你的凭证（已 gitignore）
```

### 各供应商文件索引

如果你只关心某个供应商，以下是涉及的文件：

| 供应商 | 适配器 | 元数据 | DX 评估 | 凭证位置 |
|--------|--------|--------|---------|----------|
| BNB Chain MCP | `adapters/bnbchain_mcp.py` | `providers/bnbchain_mcp.yaml` | `evaluations/bnbchain_mcp.yaml` | `config.yaml` → `providers.bnbchain_mcp` |
| Crossmint | `adapters/crossmint.py` | `providers/crossmint.yaml` | `evaluations/crossmint.yaml` | `config.yaml` → `providers.crossmint` |
| Coinbase AgentKit | `adapters/coinbase_agentkit.py` | `providers/coinbase_agentkit.yaml` | `evaluations/coinbase_agentkit.yaml` | `config.yaml` → `providers.coinbase_agentkit` + `cdp_api_key.json` |
| Privy | `adapters/privy.py` | `providers/privy.yaml` | `evaluations/privy.yaml` | `config.yaml` → `providers.privy` |
| MoonPay | `adapters/moonpay.py` | `providers/moonpay.yaml` | `evaluations/moonpay.yaml` | `config.yaml` → `providers.moonpay` |
| Minara | `adapters/minara.py` | `providers/minara.yaml` | `evaluations/minara.yaml` | `config.yaml` → `providers.minara` |
| OKX OnchainOS | `adapters/okx_onchainos.py` | `providers/okx_onchainos.yaml` | `evaluations/okx_onchainos.yaml` | `config.yaml` → `providers.okx_onchainos` |
| Clawlett | `adapters/clawlett.py` | `providers/clawlett.yaml` | `evaluations/clawlett.yaml` | `config.yaml` → `providers.clawlett` |
| Para Wallet | `adapters/para_wallet.py` | `providers/para_wallet.yaml` | `evaluations/para_wallet.yaml` | `config.yaml` → `providers.para_wallet` |
| Universal Trading | `adapters/universal_trading.py` | `providers/universal_trading.yaml` | `evaluations/universal_trading.yaml` | `config.yaml` → `providers.universal_trading` |
| Polymarket Agent | `adapters/polymarket_agent.py` | `providers/polymarket_agent.yaml` | `evaluations/polymarket_agent.yaml` | `config.yaml` → `providers.polymarket_agent` |
| Coinpilot Hyperliquid | `adapters/coinpilot_hyperliquid.py` | `providers/coinpilot_hyperliquid.yaml` | `evaluations/coinpilot_hyperliquid.yaml` | `config.yaml` → `providers.coinpilot_hyperliquid` |

> 所有供应商共享 `adapters/base.py`（基类）和 `cases/shared/`（测试用例）。运行任何供应商都需要这些文件加上 `runner.py`。

## 深入了解

| 文档 | 内容 |
|------|------|
| [测试设计思路](docs/methodology/test-design-philosophy.md) | 为什么选这些测试项？覆盖了哪些风险？评分逻辑是什么？ |
| [测试项详解](docs/methodology/test-item-reference.md) | 每个测试具体做了什么、怎么判定通过、为什么重要 |
| [候选评测对象与未来方向](docs/next-steps.md) | 下一步计划加入哪些供应商、筛选标准和优先级 |

## 查看结果

运行测试后，打开 Dashboard 查看：

```bash
open web/index.html
```

结果保存在 `results/`（已 gitignore）：
- `results/public_results.json` — 脱敏后的聚合结果（可安全分享）
- `results/private_debug_<provider>.json` — 完整调试输出（含地址/签名）

> **关于 Dashboard 中的"AI 洞察"**：功能对比卡片和详情页中的 AI 洞察文案是基于项目维护者的测试结果撰写的静态内容。如果你自行运行测试，测试通过率和延迟数据会根据你的实际结果动态更新，但 AI 洞察文案中引用的具体数字（如延迟、评分）可能与你的结果有出入。图表、表格、通过率等数据均为实时计算，不受此影响。

## License

MIT
