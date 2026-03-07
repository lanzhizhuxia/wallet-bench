---
title: 'ISSUE-015: Bundler Nonce 实时健康监控'
concepts:
- real-time-monitoring
- anomaly-detection
- competitive-intelligence
---
# ISSUE-015: Bundler Nonce 实时健康监控

## Meta
- **Status**: DEPRECATED
- **Priority**: ~~P3~~ N/A
- **Component**: scripts/, web/app.js
- **Owner**: TBD
- **Date**: 2026-03-07
- **Effort**: Medium (~4-8h)
- **Blocked By**: 无
- **Blocks**: 无
- **Deprecated Date**: 2026-03-07
- **Deprecation Reason**: Oracle 审核判定为 P3 运维健康信号，非用户牵引力指标；不符合 a.y 核心需求（竞品商业牵引力雷达）。经确认废弃。

## Background

ISSUE-012 发现 Crossmint 主网专用 bundler `0x9d4c1c9e...`，其 nonce 代表累计交易总数：
- Base: 642,342
- Arbitrum: 20,974
- Optimism: 4,886

Bundler nonce 可以通过一次 `eth_getTransactionCount` RPC 调用获取，无需扫描事件日志。
定期采集 nonce 增量 = 该周期内的交易量，比 BundleBear T+1 延迟更实时。

## 目标

1. 定期采集 Crossmint bundler nonce，计算增量作为交易量代理指标
2. 提供异常检测（交易量骤降 = 可能故障）
3. 同理可扩展到 Coinbase 等其他有专用 bundler 的供应商

## 任务分解

### Task 1: Nonce 采集脚本

新增轻量采集函数，支持每小时或每日运行：
```python
def collect_bundler_nonce(bundler_addr: str, rpc_url: str) -> int:
    # eth_getTransactionCount(bundler_addr, "latest")
```

输出格式：
```json
{
  "provider": "crossmint",
  "bundler": "0x9d4c1c9e...",
  "chain": "base",
  "nonce": 643210,
  "delta_24h": 868,
  "collected_at": "2026-03-07T12:00:00Z"
}
```

### Task 2: 历史 nonce 文件 + 增量计算

- 保存每次采集的 nonce 到 `web/data/market_nonce.json`
- 计算与上次采集的差值 = 期间交易量
- 保留最近 30 天历史

### Task 3: Dashboard 展示

在链上数据卡片中增加 "实时交易量" 子区域：
- 显示 24h nonce 增量
- 趋势 sparkline（最近 7 天）
- 异常标记：如果 24h 增量 < 历史均值的 20%，显示警告

### Task 4: 异常告警（可选）

- GitHub Actions 中增加阈值检测
- 如果 nonce 增量异常，创建 issue 或发送通知

## 成功标准

- [ ] 每日自动采集 Crossmint bundler nonce
- [ ] Dashboard 展示 24h 交易量增量
- [ ] 异常检测有基本实现（阈值比较）

## 风险

| 风险 | 影响 | 缓解 |
|------|------|------|
| Bundler 地址更换 | 数据断裂 | 定期验证 bundler 是否仍活跃（nonce 是否增长） |
| RPC 限流 | 采集失败 | 单次仅 1 个 RPC 调用，极低负载；加重试 |
| Nonce 包含非 UserOp 交易 | 数据有噪声 | Bundler 专用于 AA，非 UserOp 交易极少 |

## 扩展性

该方案可直接复用到任何有专用 bundler 的供应商：
- Coinbase：如果发现其专用 bundler，同样接入
- 其他 WaaS：同理
