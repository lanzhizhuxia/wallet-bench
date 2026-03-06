---
name: Provider Request
about: 提交一个新的钱包供应商加入 benchmark
title: "[Provider Request] <供应商名称>"
labels: provider-request
assignees: ''
---

## 基本信息

- **供应商名称**：
- **官网**：
- **架构类型**（local / delegated / intent / custodial / tee / mpc_aa）：
- **托管模型**（如 Local、TEE+Shard、Custodial 等）：

## SDK / 集成方式

- **GitHub**：
- **包名**：
- **包管理器**（npm / pypi / 其他）：
- **文档链接**：
- **集成方式**（选一个或多个）：
  - [ ] MCP Server (stdio)
  - [ ] REST API
  - [ ] Python SDK
  - [ ] CLI
  - [ ] 其他：___

## 能力信息

- **支持的链**（如 ethereum, base, solana 等）：
- **签名模式**（如 personal_sign, eip712, raw_tx 等）：
- **交易提交方式**（client_submit / provider_submit）：
- **所需凭证**（如 API_KEY, PRIVATE_KEY 等，只填名称，不要填真实值）：
- **是否有测试网**：Yes / No
  - 测试网名称：
  - 水龙头链接：

## Provider YAML 模板

如果你熟悉本项目的结构，欢迎直接填写以下 YAML（参考 `providers/` 目录下的现有文件）：

```yaml
name: 供应商名称
class: local          # local / tee / intent / mpc_aa
custody_model: Local  # Local / TEE+Shard / Custodial / Fireblocks-Custodial 等
signing_modes: [personal_sign, eip712, raw_tx]
submission_mode: client_submit  # client_submit / provider_submit
chains: [ethereum, base]
required_secrets: [API_KEY]
network_modes:
  testnet: sepolia
  mainnet: ethereum
viability: unknown  # ready / blocked / unknown

skill:
  github: ""
  package: ""
  package_registry: ""  # npm / pypi
  integration_type: ""  # mcp_server_stdio / python_sdk / rest_api / cli_subprocess
  docs_url: ""
  description: ""
  license: ""

governance:
  policy_engine: false
  spend_limit: false
  address_allowlist: false
  human_in_loop: false
  notes: ""
```

## 为什么应该加入？

<!-- 简要说明这个供应商的独特价值或使用场景 -->

## 补充信息

<!-- 其他有助于评估的信息（定价模式、独特功能、已知限制等） -->
