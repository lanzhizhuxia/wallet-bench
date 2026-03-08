# wallet-bench Issue Index

**Last Updated**: 2026-03-08 (ISSUE-026 Dashboard v2 场景选择器 + FitScore + 覆盖度徽章)

## Current Execution Focus

| Issue ID  | Stage    | Title                                                    | Status      | Priority | User Value                                                                                       | Link                                                              |
| --------- | -------- | -------------------------------------------------------- | ----------- | -------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------- |
| ISSUE-001 | Done     | 钱包 Skill 横向对比测试平台 — Adapter + Runner + Web 可视化 | MILESTONE_COMPLETE | P1 | 标准化测试 Tier 1-3 钱包 Skill 的 Key 管理/签名/交易能力，通过 Web 展示对比结果，辅助技术选型决策。 | docs/issues/active/ISSUE-001-wallet-skill-benchmark/ |
| ISSUE-002 | Done     | 双层展示重构 — 底层架构 vs Skill 层分离 + Skill 元数据补全       | ACCEPTED    | P1       | 将 benchmark 结果分为底层架构对比和 Skill DX 对比两层展示，补全 skill 元数据（GitHub/包名/集成方式），服务决策者选型决策。 | docs/issues/active/ISSUE-002-two-layer-presentation/ |
| ISSUE-003 | Done     | Web UI 架构重组 + 交互增强                                    | COMPLETE    | P1       | 4 Tab 导航重构 + 需求筛选器 + 雷达图 toggle + 踩坑总结 + Runner 多次运行 + 12 个 BUG 修复。 | docs/issues/active/ISSUE-003-ui-polish/ |
| ISSUE-004 | Done     | Binance 设计风格迁移                                          | COMPLETE    | P1       | 将 GitHub Dark 主题迁移至 Binance Dark Midnight（纯黑底、黄色强调、DM Sans 字体），对齐品牌视觉。 | docs/issues/active/ISSUE-004-binance-design-migration/ |
| ISSUE-005 | Done     | 详情页 UX 增强                                                | COMPLETE    | P1       | 详情页信息层级重构：结论条、语义化配色、测试表筛选/排序、Memo 折叠、Card 布局优化。 | docs/issues/active/ISSUE-005-detail-page-ux-enhancement/ |
| ISSUE-006 | Done     | 测试分类重构 — 基础设施 vs 应用层分离 + DeFi/Swap 新维度     | COMPLETE    | P1       | 新增 Swap/DeFi/Bridge/预测市场/永续合约测试维度，区分 infra vs app 层，N/A 不入评分分母，筛选器改为 PM 视角两层结构。 | docs/issues/active/ISSUE-006-test-taxonomy-restructure/ |
| ISSUE-007 | Done     | 基础能力细分 — 钱包基础/权限治理/稳定性/运维能力四维度       | COMPLETE    | P2       | 将基础能力 13 项测试拆为 4 个子维度，PM 可按关注点精准筛选，矩阵表分组更清晰。 | docs/issues/active/ISSUE-007-infra-sub-dimensions/ |
| ISSUE-008 | Done     | 测试矩阵扩展 — App 层真实测试 + Crossmint 升级 + 数据可信度            | COMPLETE   | P1       | Batch 1-6 全部完成。6 provider 全量真实测试运行，数据溯源 badge + 覆盖率横幅 + YAML 视觉降级。 | docs/issues/active/ISSUE-008-test-matrix-expansion/ |
| ISSUE-009 | Done     | 功能对比融合 DeFi 集成难度矩阵                                          | COMPLETE   | P1       | DeFi 场景评级（即用/低门槛/中等/不可行）融入功能对比卡片和详情页，替代旧 app_layer 雷达维度。 | docs/issues/active/ISSUE-009-comparison-defi-fusion/ |
| ISSUE-010 | Done     | 一级导航重构 — 评测合并 + 知识阅读扩充                                  | COMPLETE   | P1       | 3 Tab 导航重构 + 了解更多子 Tab（测试设计/测试详解/下一步）+ Markdown 渲染。 | docs/issues/active/ISSUE-010-nav-restructure/ |
| ISSUE-011 | Done     | 竞品活跃度监控 — 链上数据 + SDK 下载量 + 社区指标                       | COMPLETE | P2 | 6 维度日频自动采集（npm/PyPI/GitHub/StatusPage/Docs/链上）+ Dashboard Market Tab + BundleBear API stale 降级。Phase 3 废弃（季度人工流程）。 | docs/issues/active/ISSUE-011-competitor-monitoring/ |
| ISSUE-012 | Done     | Crossmint 链上工厂合约反查 — 通过自测钱包提取 factory 地址               | DONE       | P2       | 确认 Crossmint 精准归因：`trackable: true`。Factory `0xd703aae...` + Bundler `0x9d4c1c9e...` 组合，主网+测试网均验证。 | docs/issues/active/ISSUE-012-crossmint-onchain-attribution/ |
| ISSUE-013 | Done     | Privy 链上归因突破 — Paymaster / Bundler 足迹调研                        | CLOSED     | P2       | 确认 Privy 链上不可追踪：paymaster 由开发者自配，Native Sponsorship 地址未公开，两条路径均失败。 | docs/issues/active/ISSUE-013-privy-paymaster-attribution/ |
| ISSUE-014 | Done | Crossmint vs Coinbase 竞争力对比可视化                                    | DONE | P2       | Task 1-3 全部完成：双线对比图 + 链偏好堆叠条 + 7d WoW badge + 30d 趋势箭头。 | docs/issues/active/ISSUE-014-competitive-comparison-viz/ |
| ISSUE-015 | Deprecated | Bundler Nonce 实时健康监控                                                | DEPRECATED | ~~P3~~ | 废弃——Oracle 审核判定为运维健康信号，非用户牵引力指标，不符合核心需求。 | docs/issues/active/ISSUE-015-bundler-nonce-monitoring/ |
| ISSUE-016 | Done | 新增 Clawlett Provider — Smart Account (Gnosis Safe + Zodiac Roles) | DONE | P0 | Smart Account 原生架构 + Zodiac Roles 细粒度权限引擎，填补 governance 维度空白，自带 MEV 保护。 | docs/issues/active/ISSUE-016-clawlett-provider/ |
| ISSUE-017 | Done | 新增 Para Wallet Provider — 纯 MPC 钱包基础设施 | DONE | P1 | 纯 MPC 私钥分片，唯一覆盖 EVM + Solana + Cosmos 三链族的 Skill，与 Privy 直接竞品对标。 | docs/issues/active/ISSUE-017-para-wallet-provider/ |
| ISSUE-018 | Done | 新增 Universal Trading Provider — Particle Network 跨链交易 | DONE | P2 | 跨链交易覆盖最广 + Solana MEV Tip + WebSocket 实时监控，验证 Universal Account 场景。 | docs/issues/active/ISSUE-018-universal-trading-provider/ |
| ISSUE-019 | Done | 新增 Polymarket Agent Provider — 预测市场垂直场景验证 | DONE | P3 | 验证 t17 (prediction_market) 测试项真实可行性，目前 7 provider 均未通过。 | docs/issues/active/ISSUE-019-polymarket-agent-provider/ |
| ISSUE-020 | Done | 新增 Coinpilot Hyperliquid Provider — 永续合约垂直场景验证 | DONE | P3 | 验证 t18 (perps_trading) 测试项真实可行性，目前 7 provider 均未通过。 | docs/issues/active/ISSUE-020-coinpilot-hyperliquid-provider/ |
| ISSUE-021 | Done | 测试维度扩展 33→45 项 | DONE | P0 | Security/Compliance/Agent 三个新维度 + 12 个 P0 测试项 + 评分体系改造，测试覆盖从 33 项扩展至 45 项 | docs/issues/ISSUE-021-test-dimension-expansion.md |
| ISSUE-022 | Done | Para Wallet + Universal Trading 适配器修复 | DONE | P1 | 修复 hex 编码/地址解析 bug，Universal Trading 分数 33.3%→50.0% | docs/issues/ISSUE-022-adapter-bugfix.md |
| ISSUE-023 | Done | Dashboard 双层分类 UI + OKX 测试补全 | DONE | P0 | OKX 加入 decision_view、12 provider 全量 45 测试对齐、Dashboard tier-aware 分组（WaaS vs OpenClaw Skill）、CSS tier badge | — |
| ISSUE-024 | Done | 评分体系 v2 — 9 维雷达 + 双评分公式 + 维度权重重构 | DONE | P0 | 应用场景独立计分（不惩罚专精型）、Agent/性能提权、治理安全运维合并为企业就绪度 | docs/issues/ISSUE-024-scoring-v2.md |
| ISSUE-025 | Done | 新增测试项 — App 场景扩充 + Agent 自主性 + 性能基准 | DONE | P0 | 21 项新测试：Swap 6 项 + DeFi/跨链/预测各 1 项 + Agent 6 项 + 性能 6 项，总计 45→66 | docs/issues/ISSUE-025-new-test-items.md |
| ISSUE-026 | Done | Dashboard v2 — 场景选择器 + FitScore 排序 + 覆盖度徽章 | DONE | P1 | 9 维雷达、场景选择器按 FitScore 排序、PlatformScore 用 AppTop2 不惩罚专精、Coverage 徽章 | docs/issues/ISSUE-026-dashboard-v2.md |
