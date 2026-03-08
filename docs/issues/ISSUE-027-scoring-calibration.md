# ISSUE-027: 评分修正 + 判定收紧 + DeFi Matrix 补全

**Status**: DONE
**Priority**: P0
**Date**: 2026-03-08

## Summary

Oracle 战略审核建议：先修正会误导选型决策的评分/判定偏差，再跑全量测试。

## Changes

### Task 1: MoonPay 场景评分修正
- `moonpay.uniswap_swap` 从 `not_feasible` → `ready_to_use_conditional`
- 原因：MoonPay `mp token swap` 是内置聚合器兑换，支持通用 Token Swap 意图
- 影响：swap 雷达维度 0→80，Coverage 0/5→1/5

### Task 2a: ag01 tool_discovery 阈值收紧
- `_MIN_CAP_ENTRIES` 5→8，`_MIN_PUBLIC_METHODS` 5→10
- 新增 `discovery_quality` 三档区分：full / dedicated / basic

### Task 2b: _looks_like_success 长文本假阳性修复
- 6 个文件：d01, m01, x01, t16, t17, t18
- 长文本不再无条件 True，先检查前 500 字符有无 ≥2 个失败信号

### Task 2c: SCENARIO_SUPPORT_THRESHOLD 常量提取
- `web/app.js` 新增 `const SCENARIO_SUPPORT_THRESHOLD = 5`
- 替换所有 5 处硬编码的 `>= 5` / `< 5` 判定

### Task 3: DeFi Matrix 补全 6 家 Provider
- 新增：okx_onchainos, clawlett, para_wallet, universal_trading, polymarket_agent, coinpilot_hyperliquid
- defi_matrix.v1.json providers 6→12, ratings 6→12
- decision_view.v1.json 同步更新评级数据

### 评级调整汇总
| Provider | uniswap_swap | aave_morpho | hyperliquid | polymarket |
|---|---|---|---|---|
| okx_onchainos | ready_to_use_conditional | not_feasible | not_feasible | not_feasible |
| clawlett | ready_to_use_conditional | moderate | not_feasible | not_feasible |
| para_wallet | low_barrier | low_barrier | moderate | moderate |
| universal_trading | ready_to_use_conditional | not_feasible | not_feasible | not_feasible |
| polymarket_agent | not_feasible | not_feasible | not_feasible | ready_to_use |
| coinpilot_hyperliquid | not_feasible | not_feasible | ready_to_use_conditional | not_feasible |

## Files Modified
- `docs/data/defi_matrix.v1.json`
- `web/data/decision_view.v1.json`
- `web/app.js`
- `cases/shared/ag01_tool_discovery.py`
- `cases/shared/d01_farm_combo.py`
- `cases/shared/m01_market_combo.py`
- `cases/shared/x01_arb_atomicity.py`
- `cases/shared/t16_cross_chain_bridge.py`
- `cases/shared/t17_prediction_market.py`
- `cases/shared/t18_perps_trading.py`
