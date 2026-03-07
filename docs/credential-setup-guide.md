# 凭证申请指南 — 5 家 OpenClaw Skills

> 以下 5 家均来自 OpenClaw ClawHub 生态，是 Agent 技能插件。按操作复杂度从低到高排列，预计总耗时 1–2 小时。

---

## 1. Para Wallet（最简单，~5 分钟）

**需要**: API Key

### 步骤

1. 访问 [Para Developer Portal](https://developer.getpara.com)，注册/登录
2. 创建项目 → 进入 API Keys 页面
3. 创建一个 API Key，复制下来（格式通常为 `para_xxx...`）
4. 填入 `config.yaml`：

```yaml
providers:
  para_wallet:
    api_key: "你的_PARA_API_KEY"
    base_url: "https://api.beta.getpara.com"   # Beta 环境，正式环境改 api.getpara.com
    user_identifier: "wallet-bench@test.com"    # 任意邮箱标识
    chain: ethereum
```

### 验证

```bash
python runner.py run --provider para_wallet --config config.yaml
```

成功标志：`t01_create_wallet` 状态为 `pass`（创建 MPC 钱包成功）。

### 注意事项
- Beta 环境免费，但 API 有请求频率限制
- Para 文档：https://docs.getpara.com

---

## 2. Polymarket Agent（~10 分钟）

**需要**: 安装 `polymarket-agents` Python 包 + 运行 `poly setup`

### 步骤

1. 安装 CLI：

```bash
pip install polymarket-agents
```

2. 初始化钱包（会在本地创建密钥）：

```bash
poly setup
```

按提示完成设置。会生成一个 Polygon 地址。

3. 验证安装：

```bash
poly doctor    # 检查环境
poly balance   # 查看余额（初始为 0）
```

4. `config.yaml` 不需要额外凭证，只需确保 `poly` 命令可用：

```yaml
providers:
  polymarket_agent:
    chain: polygon
```

### 验证

```bash
python runner.py run --provider polymarket_agent --config config.yaml
```

成功标志：`t01_create_wallet` 状态为 `pass`（从 `poly balance` 或 `poly doctor` 解析到地址）。

### 注意事项
- Polymarket 仅运行在 Polygon **主网**，交易需要 USDC
- 本项目不会执行真实买卖（adapter 的 `send_transaction` 返回 UNSUPPORTED）
- `poly` CLI 源码：https://github.com/Polymarket/poly-agent

---

## 3. Universal Trading / Particle Network（~15 分钟）

**需要**: 克隆仓库 + Particle 项目凭证 + 私钥

### 步骤

1. 克隆示例仓库到项目目录：

```bash
cd /Users/user/Documents/workspace/wallet-bench
git clone https://github.com/particle-network/universal-account-example.git
```

2. 安装依赖：

```bash
cd universal-account-example
npm install
```

3. 获取 Particle 项目凭证：
   - 访问 [Particle Dashboard](https://dashboard.particle.network/)
   - 注册/登录 → 创建项目
   - 获取 `PROJECT_ID`、`CLIENT_KEY`、`APP_ID`

4. 创建 `.env` 文件：

```bash
cd /Users/user/Documents/workspace/wallet-bench/universal-account-example
```

写入以下内容：

```env
PRIVATE_KEY=你的EVM私钥（无0x前缀也可以）
PARTICLE_PROJECT_ID=你的项目ID
PARTICLE_CLIENT_KEY=你的客户端Key
PARTICLE_APP_ID=你的应用ID
```

> ⚠️ 建议用测试网私钥（BSC Testnet），不要用主网私钥。

5. 填入 `config.yaml`：

```yaml
providers:
  universal_trading:
    repo_path: "./universal-account-example"
    chain: bsc
```

### 验证

```bash
python runner.py run --provider universal_trading --config config.yaml
```

成功标志：`t01_create_wallet` 从 `.env` 解析到地址。

### 注意事项
- Particle Dashboard：https://dashboard.particle.network/
- 开发文档：https://developers.particle.network/
- 测试网水龙头（BSC Testnet tBNB）：https://www.bnbchain.org/en/testnet-faucet

---

## 4. Clawlett — Gnosis Safe + Zodiac（~30 分钟，最复杂）

**需要**: Clawlett 仓库 + 预部署的 Gnosis Safe + Zodiac Roles 配置

### 步骤

1. 获取 Clawlett 仓库（如果是私有仓库，需要联系项目方获取访问权限）：

```bash
cd /Users/user/Documents/workspace/wallet-bench
# 如果是公开仓库：
git clone <clawlett-repo-url> clawlett
# 或从你已有的路径创建软链接：
# ln -s /path/to/existing/clawlett ./clawlett
```

2. 安装依赖：

```bash
cd clawlett
npm install
```

3. 配置 Gnosis Safe（需要 Base 主网）：

你需要一个已部署的 Gnosis Safe，且配置了 Zodiac Roles 模块。如果还没有：

   a. 访问 [Safe{Wallet}](https://app.safe.global/) → 切换到 Base 链 → 创建新 Safe
   b. 记录 Safe 地址
   c. 在 Safe Apps 中安装 Zodiac Roles 模块（或通过合约直接部署）
   d. 配置 Roles：授权一个 Agent 地址可调用特定合约方法

4. 创建 `config/wallet.json`（在 clawlett 仓库内）：

```json
{
  "safeAddress": "0x你的Safe地址",
  "agentKey": "0x你的Agent私钥",
  "ownerAddress": "0x你的Owner地址",
  "rpcUrl": "https://mainnet.base.org"
}
```

5. 填入 wallet-bench 的 `config.yaml`：

```yaml
providers:
  clawlett:
    safe_address: "0x你的Safe地址"
    agent_key: "0x你的Agent私钥"
    owner_address: "0x你的Owner地址"
    clawlett_repo_path: "./clawlett"
```

### 验证

```bash
python runner.py run --provider clawlett --config config.yaml
```

成功标志：`t01_create_wallet` 状态为 `pass`（返回 Safe 地址）。

### 注意事项
- ⚠️ **Clawlett 仅支持 Base 主网**（chain ID 8453），不是测试网
- 我们的 `safety.blocked_chain_ids` 默认屏蔽了 8453，交易类测试会被安全机制拦截
- 要解除 Base 主网限制：在 `config.yaml` 的 `safety.blocked_chain_ids` 中去掉 `8453`（自行承担风险）
- 即使不解除，钱包创建、签名类测试仍可运行

---

## 5. Coinpilot Hyperliquid（~20 分钟，需要平台账户）

**需要**: Coinpilot 平台账户 + coinpilot.json 配置文件

### 步骤

1. 访问 [Coinpilot](https://coinpilot.ai/) 注册账户
   - 可能需要邀请码或白名单（检查官网说明）
   - 文档：https://docs.coinpilot.ai/

2. 获取 API 凭证：
   - 登录后进入设置 → API Keys
   - 获取 API Key、用户 ID

3. 获取钱包信息：
   - Coinpilot 使用 Privy 管理钱包
   - 注册后会自动创建 Hyperliquid 钱包
   - 从平台界面或 API 获取你的 Hyperliquid 钱包地址

4. 安装 CLI 工具（如果有）：

```bash
# 检查是否需要安装 coinpilot CLI
npm install -g coinpilot   # 或通过 repo 内 scripts/coinpilot_cli.mjs
```

5. 创建 `coinpilot.json`（项目根目录）：

```json
{
  "apiKey": "你的API_KEY",
  "userId": "你的USER_ID",
  "walletAddress": "0x你的Hyperliquid钱包地址",
  "apiBaseUrl": "https://api.coinpilot.ai"
}
```

6. 填入 `config.yaml`：

```yaml
providers:
  coinpilot_hyperliquid:
    config_path: "./coinpilot.json"
    api_base_url: "https://api.coinpilot.ai"    # 可选，覆盖 json 中的值
```

### 验证

```bash
python runner.py run --provider coinpilot_hyperliquid --config config.yaml
```

成功标志：`t01_create_wallet` 返回 Hyperliquid 钱包地址。

### 注意事项
- Coinpilot 是 copy-trade 平台，交易通过订阅 leader 执行
- 5 req/s 速率限制
- 仅支持 Hyperliquid L1，不支持通用 EVM 交易

---

## 配置完成后

每配置完一个供应商，可以单独跑测试验证：

```bash
# 逐个验证
python runner.py run --provider para_wallet --config config.yaml
python runner.py run --provider polymarket_agent --config config.yaml
python runner.py run --provider universal_trading --config config.yaml
python runner.py run --provider clawlett --config config.yaml
python runner.py run --provider coinpilot_hyperliquid --config config.yaml
```

全部配置完后，跑全量测试并更新 Dashboard 数据：

```bash
# 跑全部 12 家
python runner.py run-all --config config.yaml --runs 3

# 复制结果到 web
cp results/public_results.json web/data/public_results.json

# 查看 Dashboard
open web/index.html
```

配置好后通知我，我来跑测试、更新数据、推送到 GitHub。

---

## 速查表

| 供应商 | 需要什么 | 去哪里申请 | 预计时间 |
|--------|---------|-----------|---------|
| Para Wallet | API Key | https://developer.getpara.com | 5 分钟 |
| Polymarket Agent | `pip install` + `poly setup` | 本地安装即可 | 10 分钟 |
| Universal Trading | 克隆仓库 + Particle 凭证 | https://dashboard.particle.network/ | 15 分钟 |
| Coinpilot | 平台账户 + API Key | https://coinpilot.ai/ | 20 分钟 |
| Clawlett | 仓库 + Gnosis Safe + Zodiac | https://app.safe.global/ (Base) | 30 分钟 |
