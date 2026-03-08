# ISSUE-028: v2.1 全面审查修复 — 评分偏差 + Dashboard 健壮性 + 数据补全

**Status**: TODO
**Priority**: P0
**Date**: 2026-03-09

## 背景

v2.1 基线数据完成后（12 providers × 66 tests × 3 runs），对 Dashboard 全部页面、评分系统、数据质量进行全面审查。发现 19 项问题，按优先级分为 P0/P1/P2/P3 四级。

完整审查报告: `docs/reviews/v2.1-comprehensive-review.md`

## P0 — 必须修复

### P0-1: cross_chain 维度全 0 — 扭曲雷达图和排名
- **现象**: 12 家 provider 的 cross_chain 雷达维度全 0。DeFi Matrix 无 cross_chain 场景条目，仅有的 2 个测试 (cross_chain_bridge, arb_atomicity) 全部 not_applicable/unsupported
- **影响**: 雷达图在 cross_chain 方向塌陷，Coverage 永远最多 4/5，AppTop2 只从 4 维度选
- **方案**: DeFi Matrix 增加 cross_chain 场景条目（Wormhole/Stargate 桥接评级），或暂时从雷达和 Coverage 中排除 cross_chain

### P0-2: fetch 错误处理不足 — 数据加载失败时白屏
- **现象**: app.js 4 个 fetch 调用仅 1 个 .catch()
- **方案**: 所有 fetch 加 .catch() + 用户友好错误提示

### P0-3: 市场数据只覆盖 6-7 家 — 5 家 OpenClaw Skill 无数据
- **现象**: market_npm/github/pypi.json 仅含 WaaS provider，OpenClaw Skill 完全缺失
- **方案**: 补齐 5 家 OpenClaw Skill 的 GitHub 数据，或在 Tab 中标注 "暂无"

## P1 — 应该修复

### P1-1: ag01 tool_discovery 阈值过严 — 仅 2/12 通过
- **现象**: `_MIN_PUBLIC_METHODS=10` 导致仅 bnbchain_mcp(10) 和 okx_onchainos(10) 通过，其余（含 Coinbase、Privy）因 9 methods 全部 fail
- **方案**: 降到 `_MIN_PUBLIC_METHODS=9`

### P1-2: 8 个 skip 测试膨胀展示数量
- **现象**: 8 个观察项永远 skip，UI 显示 "66 tests" 但有效仅 58 项
- **方案**: 汇总卡片标注 "58 项有效 / 8 项观察"

### P1-3: Clawlett 数据不可信 — 应加标注
- **现象**: placeholder 凭证导致 16 errors，得分 7.4% 不反映真实能力
- **方案**: Dashboard 加 "⚠️ 凭证未配置" 标注

### P1-4: next-steps.md 缺 para_wallet 和 universal_trading
- **方案**: 更新文档补全

### P1-5: 63 vs 66 测试数不一致
- **现象**: 3 家 provider 少 3 个 arch-specific 测试（跳过而非记为 N/A）
- **方案**: runner 应记为 NOT_APPLICABLE 而非跳过

## P2 — 锦上添花

### P2-1: _looks_like_success 重复 6 份
- **方案**: 提取到 `cases/shared/_utils.py`

### P2-2: Coverage 徽章缺无障碍文本
- **方案**: 加 aria-label + 旁边显示文本

### P2-3: app.js 3557 行单文件过大
- **方案**: 后续拆分模块（非紧急）

### P2-4: URL hash 未知 scenario 无降级
- **方案**: fallback 到 `all`

### P2-5: 延迟 heatmap 空白行
- **方案**: 无数据 provider 标灰 + "无数据"

### P2-6: AI Insights 文案陈旧
- **方案**: 更新适配 v2.1 数据或加声明

## P3 — 后续考虑

### P3-1: 缺 "快速选型" 入口（选场景→推荐 top 3）
### P3-2: 无 provider 并排对比功能
### P3-3: 缺套利/farming 专项测试（quote 漂移、nonce 冲突、长会话重试、approve 卫生）
### P3-4: 无历史趋势追踪
### P3-5: cross_chain 维度空转影响 AppTop2

## 建议执行顺序

1. P0-1 (cross_chain) + P0-2 (fetch 容错) + P1-1 (ag01 阈值)
2. P0-3 (市场数据) + P1-3 (Clawlett 标注) + P1-5 (63→66)
3. P2 批量处理
4. P3 下个迭代

## 涉及文件

- `web/app.js` — fetch 容错、hash 容错、Coverage 徽章无障碍、Clawlett 标注
- `web/style.css` — 标注样式
- `cases/shared/ag01_tool_discovery.py` — 阈值调整
- `cases/shared/_utils.py` — 新文件，提取公共函数
- `docs/data/defi_matrix.v1.json` — cross_chain 场景条目
- `web/data/decision_view.v1.json` — 同步
- `web/data/market_*.json` — 补齐 OpenClaw 数据
- `docs/next-steps.md` — 补全 provider 信息
- `runner.py` — arch-specific 测试记为 N/A 而非跳过
