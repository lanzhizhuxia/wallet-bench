# ISSUE-029: Post-Run Fixes (Oracle 验收修复)

**Date**: 2026-03-09
**Trigger**: Oracle 对 72-test 全量测试结果验收时发现的 3 个代码层面问题

---

## Fix 1: Dashboard 测试计数 66 → 72

**问题**: ISSUE-028 将 registry 从 66 扩展到 72（新增 6 个 arch-specific 测试：
`attestation`, `failover_continuity`, `policy_depth`, `intent_schema`, `fulfillment_sla`, `cancellation`），
但 `web/app.js` 的 `totalTestCount` / `effectiveTestCount` 未同步更新。

**修复**: `web/app.js`
- `totalTestCount`: 66 → 72
- `effectiveTestCount`: 58 → 64 (72 − 8 observation stubs)
- `observationTestCount`: 8 (不变)

---

## Fix 2: crossmint sig_verify EIP-1271 兼容

**问题**: crossmint 是 Smart Wallet（合约钱包，class: intent），`sign_message` 返回 86 bytes 签名
（65 bytes ECDSA + 21 bytes validator 数据）。`t29_sig_verify` 原逻辑直接调用
`Account.recover_message()` 要求恰好 65 bytes，导致 crossmint 误报 ERROR:
`"Unexpected recoverable signature length: Expected 65, but got 86 bytes"`

**修复**: `cases/shared/t29_sig_verify.py`
1. 将 `Account.recover_message()` 调用包装在 try/except 中
2. 标准 ecrecover 失败时（sig 长度 ≠ 65），自动尝试 EIP-1271 on-chain 验证路径
3. EIP-1271 验证: 调用合约 `isValidSignature(bytes32 hash, bytes sig)` → 返回 magic `0x1626ba7e` 即为通过
4. EIP-712 typed data 验证同样适配 smart wallet 路径

**影响**: crossmint sig_verify 从 ERROR → PASS（若 EIP-1271 验证通过）或 FAIL（若合约验证也未通过）。
需要重跑 crossmint 的 sig_verify 测试来确认最终结果。

---

## Fix 3: bnbchain_mcp N/A=20 复核

**结论**: 全部 20 个 N/A 均合理，无误判，无需修改。

**详细分解** (bnbchain_mcp: class=local, in NO_BUILTIN_APP_PROVIDERS):

### category_mismatch × 14 (app 类测试，bnbchain_mcp 无内置应用层 API)
| test_name | category |
|-----------|----------|
| token_swap | app |
| defi_interaction | app |
| cross_chain_bridge | app |
| prediction_market | app |
| perps_trading | app |
| route_discovery | app |
| slippage_guard | app |
| mev_protection | app |
| minimal_approve | app |
| post_revoke | app |
| unsafe_approve_detect | app |
| farm_combo | app |
| arb_atomicity | app |
| market_combo | app |

### architecture_mismatch_tee × 3 (TEE-only 测试，bnbchain_mcp 是 local)
| test_name | reason |
|-----------|--------|
| attestation | TEE only |
| failover_continuity | TEE only |
| policy_depth | TEE only |

### architecture_mismatch_intent × 3 (intent-only 测试，bnbchain_mcp 是 local)
| test_name | reason |
|-----------|--------|
| intent_schema | intent only |
| fulfillment_sla | intent only |
| cancellation | intent only |

**对比**: 不在 NO_BUILTIN_APP_PROVIDERS 的其他 WaaS provider 只有 6 个 N/A (3 TEE + 3 intent)。
bnbchain_mcp 额外 14 个 app 类 N/A 是因为它在 NO_BUILTIN_APP_PROVIDERS 列表中。
14 + 6 = 20，计算正确。

---

## Oracle 验收结论摘要

- 72-test 全量运行结果有效
- 3 个代码层面问题已修复（计数同步、EIP-1271 兼容、N/A 复核）
- sig_verify EIP-1271 修复需要对 crossmint 重跑该单项测试来确认最终评分
