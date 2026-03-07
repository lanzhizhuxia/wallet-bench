'use strict';

// --------------------------------------------------------------------------
// Globals & Constants
// --------------------------------------------------------------------------
let currentData = null;
let activeTab = 'comparison';
let decisionData = null;
let lastActiveTab = 'comparison';
let mainRadarChart = null;

const DEFERRED_PROVIDERS = [];

// --- Two-level navigation structure ---
const NAV_STRUCTURE = {
    overview: { label: '评测总览', defaultSub: 'comparison', subs: ['comparison', 'radar', 'latency'] },
    filter:   { label: '需求筛选', defaultSub: null, subs: [] },
    learn:    { label: '了解更多', defaultSub: 'wallet-types', subs: ['wallet-types', 'test-design', 'test-detail', 'next-steps'] },
    market:   { label: '市场活跃度', defaultSub: null, subs: [] },
};
const SUB_TO_MAIN = {};
for (const [mainId, cfg] of Object.entries(NAV_STRUCTURE)) {
    for (const sub of cfg.subs) {
        SUB_TO_MAIN[sub] = mainId;
    }
}

function getCssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
const PROVIDER_COLORS = {
  bnbchain_mcp: '#F0B90B',
  coinbase_agentkit: '#4ECDC4',
  crossmint: '#C084FC',
  privy: '#FF6B6B',
  minara: '#28A473',
  moonpay: '#60A5FA',
  okx_onchainos: '#000000',
};

const STATUS_ICONS = { pass: "✅", fail: "❌", skip: "⚠️", error: "❗️", not_applicable: "—", unsupported: "🚫", inconclusive: "❓" };
const STATUS_CLASS = { pass: "status-pass", fail: "status-fail", skip: "status-skip", error: "status-error", not_applicable: "status-na", unsupported: "status-unsupported", inconclusive: "status-inconclusive" };
const STATUS_ZH = { pass: "通过", fail: "失败", skip: "行业缺口", error: "错误", not_applicable: "不适用", unsupported: "不支持", inconclusive: "待确认" };

const TEST_NAME_ZH = {
    key_generate: "创建钱包", sign_message: "消息签名（登录验证）", sign_typed_data: "结构化签名（Permit/订单）",
    send_tx: "转账/交易", multi_chain: "多链支持", policy_enforcement: "风控拦截",
    nonce_management: "交易序号管理", tx_confirmation: "交易确认",
    session_delegation: "会话授权", concurrent_ops: "并发操作", failure_recovery: "故障恢复",
    preflight_fee: "预估手续费", derivation_path: "密钥派生路径", keychain_lock: "密钥锁定",
    backup_recovery: "备份恢复", intent_schema: "意图格式校验", fulfillment_sla: "履约时效",
    cancellation: "取消操作", attestation: "安全环境证明", failover_continuity: "故障切换恢复",
    policy_depth: "精细化风控", rate_limit_resilience: "限流恢复能力", portability_recovery: "钱包迁移恢复",
    idempotent_submit: "重复提交防护", retry_backoff: "失败重试机制",
    webhook_delivery: "事件回调通知", quota_disclosure: "配额透明度",
    authorization_audit_trace: "操作审计日志",
    policy_revocation_latency: "规则变更生效速度", denial_reason_quality: "拒绝交易时的说明",
    token_swap: "Uniswap 兑换", defi_interaction: "Aave/Morpho 借贷",
    cross_chain_bridge: "跨链桥接",
    prediction_market: "Polymarket 预测", perps_trading: "Hyperliquid 永续",
    // Phase 1 P0 (ISSUE-021)
    erc20_transfer: "ERC-20 代币转账", contract_write: "合约写入交互",
    sig_verify: "签名验证", tx_finality: "交易最终确认",
    schema_quality: "返回结构质量", machine_errors: "错误可机读性", deterministic_response: "响应确定性",
};

const TEST_DESCRIPTIONS = {
    key_generate: "验证能否通过 API 生成新密钥对并返回有效地址",
    sign_message: "验证能否对任意文本消息进行 personal_sign 签名",
    sign_typed_data: "验证能否按 EIP-712 标准对结构化数据签名",
    send_tx: "验证能否构建、签名并提交链上交易（testnet）",
    multi_chain: "验证 adapter 声明的多链支持实际可用",
    nonce_management: "验证交易序号（nonce）是否正确递增，防止交易卡住或覆盖",
    tx_confirmation: "验证提交交易后能否正确等待链上确认并返回回执",
    policy_enforcement: "验证策略引擎能否拦截超限/违规交易",
    session_delegation: "验证能否创建受限会话密钥或委托签名权限",
    concurrent_ops: "验证 3 并发操作（创建钱包/签名）的正确性和线程安全",
    failure_recovery: "验证 adapter teardown 后重新 setup 能否恢复工作",
    preflight_fee: "验证能否在交易前预估 gas 费用",
    derivation_path: "验证本地钱包的 BIP-44 派生路径是否正确（Local 类专属）",
    keychain_lock: "验证本地密钥存储的加密锁定机制（Local 类专属）",
    backup_recovery: "验证本地钱包的备份与恢复流程（Local 类专属）",
    intent_schema: "验证意图格式是否符合 provider 规范（Intent 类专属）",
    fulfillment_sla: "验证异步操作的履约时间是否在 SLA 内（Intent 类专属）",
    cancellation: "验证能否取消待处理的异步操作（Intent 类专属）",
    attestation: "验证 TEE 远程证明报告的获取和验证（TEE 类专属）",
    failover_continuity: "验证 TEE 故障切换后钱包连续性（TEE 类专属）",
    policy_depth: "验证策略引擎的细粒度规则能力（TEE 类专属）",
    rate_limit_resilience: "验证 burst 请求后 adapter 的恢复能力",
    idempotent_submit: "验证同一笔交易重复提交时不会产生重复上链",
    retry_backoff: "验证请求失败后是否支持自动退避重试",
    portability_recovery: "验证钱包身份在 teardown/setup 后的可移植性和确定性",
    webhook_delivery: "验证关键事件（交易完成、策略触发等）能否通过回调通知到外部系统",
    quota_disclosure: "验证 API 是否透明披露调用配额和剩余额度",
    authorization_audit_trace: "验证钱包/签名/交易结果中的审计字段完整性",
    policy_revocation_latency: "验证策略规则撤销后生效的延迟时间",
    denial_reason_quality: "验证交易被拒绝时返回的原因是否清晰、可操作",
    token_swap: "验证能否通过内置工具完成代币兑换（如 USDC→USDT）",
    defi_interaction: "验证能否与 DeFi 借贷协议交互（如 Aave 存款、Morpho 借贷）",
    cross_chain_bridge: "验证能否通过内置工具完成跨链资产转移",
    prediction_market: "验证能否在预测市场（如 Polymarket）下注或交易",
    perps_trading: "验证能否在永续合约平台（如 Hyperliquid）开仓/平仓",
    // Phase 1 P0 (ISSUE-021)
    erc20_transfer: "验证能否构造并提交 ERC-20 transfer calldata 交易",
    contract_write: "验证能否处理带 data 字段的合约写入交易",
    sig_verify: "验证签名后 ecrecover 恢复的地址与钱包地址一致",
    tx_finality: "验证交易提交后能否获取 receipt 并达到确认深度",
    schema_quality: "验证成功/失败路径返回的数据结构是否完整可机读",
    machine_errors: "验证错误信息是否可捕获、非空、且同类错误稳定一致",
    deterministic_response: "验证相同输入多次调用返回的结构字段是否一致",
};


const CHAIN_NAME_MAP = {
    'ethereum': 'ETH', 'ethereum-sepolia': 'ETH', 'base': 'Base', 'base-sepolia': 'Base',
    'polygon': 'Polygon', 'polygon-amoy': 'Polygon', 'arbitrum': 'Arbitrum', 'arbitrum-sepolia': 'Arbitrum',
    'optimism': 'Optimism', 'optimism-sepolia': 'Optimism', 'solana': 'Solana', 'solana-devnet': 'Solana',
    'bsc': 'BSC', 'bsc-testnet': 'BSC', 'opbnb': 'opBNB', 'opbnb-testnet': 'opBNB',
    'bitcoin-spark': 'BTC-Spark',
};

const TECH_FIELD_ZH = {
    client_submit: '客户端提交', server_submit: '服务端提交', provider_submit: '服务端提交',
    intent_async: '异步意图提交',
    raw_tx: '原始交易签名', personal_sign: '个人消息签名', eip712: 'EIP-712 结构化签名',
    secp256k1_raw: 'secp256k1 原生签名',
    'Local': '本地托管', 'TEE+Shard': 'TEE+分片托管', 'Fireblocks-Custodial': 'Fireblocks 第三方托管',
    'CDP-Server-Wallet': 'CDP 服务端钱包', 'Custodial-Smart-Wallet': '托管智能钱包',
};

const SIGNING_MODE_DESC = {
    raw_tx: '构建并签名原始交易（转账、合约调用等），最基础的链上操作能力',
    personal_sign: '对任意文本消息签名（如登录验证、链下授权），不上链',
    eip712: '对结构化数据签名（如 Permit2 授权、订单），钱包可展示可读内容供确认',
    secp256k1_raw: '直接用私钥对原始哈希签名，绕过 RLP 编码，用于自定义签名协议',
};

const AI_INSIGHTS = {
    privy: {
        title: '签名能力最全面的 TEE 方案，唯一内建企业级策略引擎',
        body: '全量通过 6 项核心签名测试（含 EIP-712），签名延迟仅 ~170ms，是六家中最快的。DeFi 场景全覆盖（4/4），但 Hyperliquid 因使用自定义 EIP-712 domain（chainId 1337/421614）需 Agent 自行构造 typed data（低门槛，~1-2d），Swap/借贷/预测仍需 agent 自行编码 calldata（1-3d）。独有的 Policy Engine + Key Quorum 机制让它成为唯一能在链下做"转账前风控"的方案——如果业务需要 Agent 自动执行交易且必须有审批流，这是当前唯一选项。接入需 Privy Dashboard 注册（人工一次），之后 MCP Server npx 一键启动即可。',
    },
    coinbase_agentkit: {
        title: 'DeFi 开箱即用能力最强，内置 Swap/Aave/Morpho action，无需手写 calldata',
        body: 'DeFi 等权分 76.2（六家最高），Swap/借贷两大核心场景内置 action 即用（🟢），得益于 CDP 内置 ActionProvider 直接封装了 0x 聚合器、Aave V3、Morpho 操作。Hyperliquid 虽有 sign_typed_data API 但无内置 action，需 Agent 自行构造 typed data（低门槛，~1-2d）。SDK 封装度高，错误信息清晰（Pydantic 校验），内置 faucet 可自动领测试币。但 onboarding 最重——需要三个独立凭证（API Key + API Secret + Wallet Secret），分散在 CDP Portal 不同页面。Polymarket 因 Polygon 链支持未验证降为中等。适合已有 Coinbase 生态的团队快速上线 DeFi Agent。',
    },
    crossmint: {
        title: '文档最成熟的托管方案，企业级 REST API 设计，但异步签名带来秒级延迟',
        body: 'Fireblocks TEE 后端提供机构级密钥安全，Smart Wallet（ERC-4337）架构。API 设计清晰（OpenAPI spec），错误信息带字段级路径提示。DeFi 四场景全覆盖——Uniswap/Aave/Hyperliquid 均为低门槛（🟡，1-2d），Polymarket 为中等（🟠，2-3d），所有 DeFi 操作需 agent 自行编码 ABI + calldata，Crossmint 只负责签名和提交。关键限制：签名是异步操作（~10s），比本地方案慢 500 倍；Staging 环境钱包无法充值，send_tx 必定 revert。适合对安全合规要求高、不急于毫秒级响应的企业场景。',
    },
    bnbchain_mcp: {
        title: '接入门槛最低的 MCP 原生方案，但签名能力缺失严重限制 DeFi 场景',
        body: '零注册零配置，只需一个 PRIVATE_KEY 即可 npx 启动，是六家中上手最快的（~8min）。支持 write_contract 调用任意合约，Swap/借贷场景可行但需 2-3d 手动编码。致命短板：不支持 personal_sign 和 EIP-712 签名，导致 Hyperliquid（🔴）和 Polymarket（🔴）均不可行——Hyperliquid 需要 EIP-712 签名授权，Polymarket 需要 EIP-712 签名且运行在 Polygon 而非 BSC。DeFi 覆盖仅 2/4，等权分 26.2。MCP 协议标准化是优势，但参数命名不一致（同一 server 内 toAddress vs to）、无独立文档（只能 list_tools() 运行时摸索），增加了 agent 集成的试错成本。适合 BSC 生态内的简单转账/合约交互场景。',
    },
    moonpay: {
        title: '工具链最丰富的本地钱包（54 工具/10 链），但缺少 raw calldata 和 EIP-712 能力',
        body: '非托管 BIP39 HD 钱包，密钥本地加密存储（OS Keychain）。一次 wallet create 即生成 10 链地址，CLI --json 输出对 AI agent 友好，还有 mp mcp 一键 MCP server。但所有交易接口都是高层封装（build+sign+broadcast 一体化），无法构建自定义 calldata 交易——Uniswap Swap 和 Aave 借贷直接不可行（🔴）。仅支持 personal_sign，不支持 EIP-712 signTypedData，导致 Hyperliquid 和 Polymarket 均不可行（🔴）。DeFi 四场景全部不可行，覆盖 0/4，等权分 0。适合标准转账、bridge、Swap 聚合器等不需要底层合约交互的场景。',
    },
    minara: {
        title: '一站式 DeFi 助手（内置 swap/perps/transfer），但完全托管且无签名原语',
        body: 'Custodial Smart Wallet 架构，密钥完全由服务端托管，无任何签名 API 暴露。内置 swap 命令可做聚合器级别的Token Swap（Simple†），但无法直接调用 Uniswap V3 Router。借贷/永续/预测均不可行（🔴），DeFi 等权分 20.0。技术测试通过率最低（38.1%），8 pass / 7 fail / 6 unsupported。--json flag 不输出 JSON、token 选择器弹出交互式 UI 阻塞自动化等问题增加集成摩擦。唯一亮点是内置 HITL 确认流（-y 可跳过）。适合对密钥控制无要求、只需简单 DeFi 操作的轻量场景。',
    },
    okx_onchainos: {
        title: '覆盖面最广的链上操作网关（60+ 链），内置 DEX 聚合 + Swap 报价，但无签名原语',
        body: '本地 Rust CLI 工具，5 skill / 34 命令，覆盖 Portfolio 查询、DEX 行情、Swap 报价、代币搜索、链上网关。60+ 链支持是七家中最广。内置 swap quote 命令提供 DEX 聚合级别报价，gateway 模块支持 gas 预估和交易模拟。但不暴露 sign_message / sign_typed_data 签名原语，也不做密钥托管——定位为"查询+报价+网关"而非"签名+提交"。需要 OKX API 凭证（API Key + Secret + Passphrase）。适合 Agent 需要跨链查询、比价、获取 Swap 报价但使用自己签名方案的场景。',
    },
};

const TEST_CATEGORY = {
    // 钱包基础 (wallet_core)
    key_generate: 'wallet_core', sign_message: 'wallet_core', sign_typed_data: 'wallet_core',
    send_tx: 'wallet_core', multi_chain: 'wallet_core', preflight_fee: 'wallet_core',
    nonce_management: 'wallet_core', tx_confirmation: 'wallet_core',
    erc20_transfer: 'wallet_core', contract_write: 'wallet_core',
    // 权限治理 (governance)
    policy_enforcement: 'governance', session_delegation: 'governance',
    authorization_audit_trace: 'governance',
    policy_revocation_latency: 'governance', denial_reason_quality: 'governance',
    // 稳定性 (reliability)
    concurrent_ops: 'reliability', failure_recovery: 'reliability',
    rate_limit_resilience: 'reliability',
    idempotent_submit: 'reliability', retry_backoff: 'reliability',
    tx_finality: 'reliability',
    // 运维能力 (ops)
    portability_recovery: 'ops', webhook_delivery: 'ops', quota_disclosure: 'ops',
    derivation_path: 'ops', keychain_lock: 'ops', backup_recovery: 'ops',
    intent_schema: 'ops', fulfillment_sla: 'ops', cancellation: 'ops',
    attestation: 'ops', failover_continuity: 'ops', policy_depth: 'ops',
    // 应用能力 (app)
    token_swap: 'app', defi_interaction: 'app', cross_chain_bridge: 'app',
    prediction_market: 'app', perps_trading: 'app',
    // 安全性 (security) — ISSUE-021
    sig_verify: 'security',
    // Agent 可用性 (agent) — ISSUE-021
    schema_quality: 'agent', machine_errors: 'agent', deterministic_response: 'agent',
};

const TEST_SOURCE = {
  // AUTO tests
  'key_generate': 'auto', 'sign_message': 'auto', 'sign_typed_data': 'auto',
  'send_tx': 'auto', 'multi_chain': 'auto', 'preflight_fee': 'auto',
  'nonce_management': 'auto', 'tx_confirmation': 'auto',
  'policy_enforcement': 'auto', 'session_delegation': 'auto',
  'authorization_audit_trace': 'auto', 'policy_revocation_latency': 'auto',
  'denial_reason_quality': 'auto',
  'concurrent_ops': 'auto', 'failure_recovery': 'auto',
  'rate_limit_resilience': 'auto', 'idempotent_submit': 'auto', 'retry_backoff': 'auto',
  'portability_recovery': 'auto', 'webhook_delivery': 'auto', 'quota_disclosure': 'auto',
  'derivation_path': 'auto', 'keychain_lock': 'auto', 'backup_recovery': 'auto',
  // 'intent_schema': 'auto', 'fulfillment_sla': 'auto', 'cancellation': 'auto', // These are TEE/Intent specific, need to check runner.py logic again
  // 'attestation': 'auto', 'failover_continuity': 'auto', 'policy_depth': 'auto',
  // HYBRID tests
  'token_swap': 'hybrid', 'defi_interaction': 'hybrid', 'cross_chain_bridge': 'hybrid',
  'prediction_market': 'hybrid', 'perps_trading': 'hybrid',
  // Phase 1 P0 (ISSUE-021)
  'erc20_transfer': 'auto', 'contract_write': 'auto', 'sig_verify': 'auto',
  'tx_finality': 'auto',
  'schema_quality': 'auto', 'machine_errors': 'auto', 'deterministic_response': 'auto',
};
// YAML-only scores are rendered separately via EVAL_SCORE_META, not in TEST_SOURCE

// Category display labels + render order
const CATEGORY_META = [
    { key: 'wallet_core', label: '钱包基础' },
    { key: 'governance', label: '权限治理' },
    { key: 'reliability', label: '稳定性' },
    { key: 'ops', label: '运维能力' },
    { key: 'app', label: '应用能力' },
    { key: 'security', label: '安全性' },
    { key: 'agent', label: 'Agent 可用性' },
];

// DeFi scenario display mappings (shared by matrix + heatmap)
const DEFI_SCENARIO_NAME_ZH = {
    'Uniswap V3 Swap': 'Uniswap Swap（兑换）',
    'Aave V3 / Morpho Blue': 'Aave / Morpho（借贷）',
    'Hyperliquid Perpetuals': 'Hyperliquid（永续合约）',
    'Polymarket Prediction': 'Polymarket（预测市场）',
};
const DEFI_RATING_LABEL_ZH = {
    '即用': '即用', '即用†': '即用†', '低门槛': '低门槛',
    '中等': '中等', '不可行': '不可行',
    // Legacy fallbacks
    'Simple': '即用', 'Simple†': '即用†', 'Medium': '低门槛',
    'Medium-Complex': '中等', 'Complex': '中等', 'Not Feasible': '不可行',
};
// Map test_name → defi scenario_id
const TEST_TO_DEFI_SCENARIO = {
    token_swap: 'uniswap_swap',
    defi_interaction: 'aave_morpho',
    perps_trading: 'hyperliquid',
    prediction_market: 'polymarket',
};

const CAP_TO_TEST = {
    create_wallet: 'key_generate', sign_message: 'sign_message', sign_typed_data: 'sign_typed_data',
    send_transaction: 'send_tx', multi_chain: 'multi_chain', policy_engine: 'policy_enforcement',
    session_keys: 'session_delegation', concurrent: 'concurrent_ops',
    token_swap: 'token_swap', defi_ops: 'defi_interaction',
    prediction: 'prediction_market', perps: 'perps_trading',
};

const CAP_NAME_ZH = {
    create_wallet: '创建钱包', sign_message: '消息签名', sign_typed_data: 'EIP-712 签名',
    send_transaction: '发送交易', multi_chain: '多链支持', policy_engine: '策略引擎',
    session_keys: '会话委托', concurrent: '并发操作',
    token_swap: 'Uniswap 兑换', defi_ops: 'Aave/Morpho 借贷',
    prediction: 'Polymarket 预测', perps: 'Hyperliquid 永续',
};

const GOV_TOOLTIPS = {
    '策略引擎': '是否有可编程的策略规则引擎',
    '限额': '是否支持交易金额限制',
    '白名单': '是否支持地址白名单过滤',
    'HITL': '是否支持人在回路确认机制 (Human-in-the-Loop)',
};

const ARCH_TOOLTIPS = {
    local: '本地托管 — 私钥存储在本地，签名在客户端完成',
    tee: 'TEE（可信执行环境）— 私钥在 TEE 中生成和使用，服务端签名',
    intent: '意图驱动 — 用户提交意图，由服务商代为执行和签名',
    mpc_aa: 'MPC + 账户抽象 — 多方计算分片密钥 + 智能合约钱包',
    unknown: '未知架构类型',
};

const ARCH_LABELS = {
    local: '本地签名',
    tee: 'TEE',
    intent: '托管签名',
    mpc_aa: '多方计算',
};

function mapChainName(c) { return CHAIN_NAME_MAP[c] || c; }
function mapTechField(v) { return TECH_FIELD_ZH[v] || v; }

function formatChains(chains, maxShow = 3) {
    if (!chains || chains.length === 0) return '—';
    const mapped = [...new Set(chains.map(mapChainName))];
    if (mapped.length <= maxShow) return mapped.join(', ');
    return mapped.slice(0, maxShow).join(', ') + ` +${mapped.length - maxShow}`;
}


// AC-003-26: Read latency with backward compat (new {median,min,max,runs_count} → fallback elapsed_ms)
function getLatencyMs(r) {
    if (r.latency && typeof r.latency.median === 'number' && r.latency.median > 0) return r.latency.median;
    return r.elapsed_ms || 0;
}

function getApplicableResults(provider) {
    return (provider.results || []).filter(r => r.status !== 'not_applicable');
}

// --------------------------------------------------------------------------
// Utility Functions
// --------------------------------------------------------------------------
function copyText(btn, text) {
    navigator.clipboard.writeText(text).then(() => {
        btn.textContent = '已复制 ✓';
        setTimeout(() => { btn.textContent = '复制'; }, 2000);
    });
}

function sanitizeText(str) {
    if (!str) return '';
    return str.replace(/\[REDACTED\]/g, '').replace(/:\s*,/g, ':').replace(/,\s*,/g, ',').replace(/\(\s*\)/g, '').replace(/\[\s*\]/g, '').replace(/,\s*$/g, '').trim();
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function localizeMessage(msg) {
    if (!msg) return '';
    return sanitizeText(msg
        // 钱包/签名/交易
        .replace(/^Created wallet\b/, '钱包已创建')
        .replace(/^Signed message\b/, '消息已签名')
        .replace(/^Signed typed data\b/, 'EIP-712 签名完成')
        .replace(/^Transaction submitted\b/, '交易已提交')
        .replace(/^Gas estimation returned successfully\b/, 'Gas 预估返回成功')
        // 跳过原因
        .replace(/^category_mismatch$/, '无内置应用层 API（如 Uniswap、Aave 等），可通过 send_transaction + calldata 实现。详见 DeFi 集成矩阵。')
        .replace(/^architecture_mismatch$/, '该测试仅适用于 local 架构的供应商。')
        .replace(/^N\/A-by-design: adapter does not support (\w+)/, '设计上不适用: adapter 不支持 $1')
        .replace(/^Skipped: adapter does not support (\w+)/, '已跳过: adapter 不支持 $1')
        .replace(/^Skipped:/, '已跳过:')
        .replace(/^Not supported by this provider/, '该服务商不支持此功能')
        // 多链
        .replace(/^Adapter declares (\d+) chains?:/, 'Adapter 声明 $1 条链:')
        // 并发
        .replace(/^(\d+) concurrent (\w+) calls? succeeded/, '$1 个并发 $2 调用成功')
        // 故障恢复
        .replace(/^All failure cases handled cleanly\b/, '所有故障场景均正常处理')
        .replace(/^Failure recovery: teardown\/setup succeeded\b/, '故障恢复: teardown/setup 成功')
        // Phase 3
        .replace(/^Rate-limit resilience: all checks passed\b/, '限流恢复: 所有检查通过')
        .replace(/^Portability: deterministic identity, all checks passed\b/, '可移植性: 确定性身份, 所有检查通过')
        .replace(/^Audit trace: (\d+)\/(\d+) checks passed\b/, '审计链: $1/$2 项检查通过')
        // Local 类
        .replace(/^Deterministic derivation confirmed\b/, '确定性派生已确认')
        .replace(/^Empty key produced distinct address\b/, '空密钥产生了不同地址')
        .replace(/^Recovery verified\b/, '恢复已验证')
        // Intent 类
        .replace(/^Intent schema validated\b/, '意图格式已校验')
        .replace(/^Fulfillment completed within SLA\b/, '履约在 SLA 内完成')
        .replace(/^Cancellation not supported\b/, '不支持取消操作')
        // TEE 类
        .replace(/^Attestation retrieved\b/, '远程证明已获取')
        .replace(/^Failover continuity confirmed\b/, '故障切换连续性已确认')
        .replace(/^Policy depth checks passed\b/, '策略深度检查通过')
        // 通用尾缀
        .replace(/checks? passed/g, '项检查通过')
        .replace(/succeeded/g, '成功')
        .replace(/not supported/gi, '不支持')
    );
}

// --------------------------------------------------------------------------
// Data Loading & Initialization
// --------------------------------------------------------------------------

function renderCoverageBanner(providers, summaryData) {
    const container = document.getElementById('coverage-banner');
    if (!container) return;

    const allTestNames = new Set();
    providers.forEach(p => {
        (p.results || []).forEach(r => allTestNames.add(r.test_name));
    });

    const executedTests = new Set();
    providers.forEach(p => {
        (p.results || []).forEach(r => {
            if (r.status && r.status !== 'not_applicable') {
                executedTests.add(r.test_name);
            }
        });
    });

    let autoCount = 0;
    executedTests.forEach(testName => {
        if (TEST_SOURCE[testName] === 'auto') {
            autoCount++;
        }
    });

    let yamlCount = 0;
    providers.forEach(p => {
        const scores = p.evaluation?.scores;
        if (scores) {
            Object.values(scores).forEach(value => {
                if (value !== null && value !== undefined) {
                    yamlCount++;
                }
            });
        }
    });

    // Based on user prompt, total is 34. Let's use a dynamic calculation but keep the user's number in mind.
    const totalTestCount = 34; // As specified in prompt
    // Derive last-updated: prefer summary.generated_at, fallback to latest provider timestamp
    let lastUpdated = 'N/A';
    if (summaryData?.generated_at) {
        lastUpdated = new Date(summaryData.generated_at).toLocaleString();
    } else {
        const timestamps = providers.map(p => p.timestamp).filter(Boolean).map(t => new Date(t).getTime());
        if (timestamps.length > 0) lastUpdated = new Date(Math.max(...timestamps)).toLocaleString();
    }

    const providerCount = providers.length;
    container.innerHTML = `📊 基准套件: ${totalTestCount} 项测试 · ${providerCount} 家 Provider · ${autoCount} 自动验证 · ${yamlCount} 人工评估 · 最后更新: ${lastUpdated}`;
}
async function loadData() {
    try {
        const [mainResp] = await Promise.all([
            fetch('data/public_results.json'),
            loadDecisionData(),  // pre-load DeFi data for radar chart app dimension
        ]);
        if (!mainResp.ok) throw new Error(`HTTP ${mainResp.status}`);
        const data = await mainResp.json();
        currentData = Array.isArray(data.providers) ? data.providers : [data];
        renderCoverageBanner(currentData, data.summary);
        handleRouting();
    } catch (err) {
        document.getElementById("overview-section").innerHTML =
            `<p class="loading">加载失败: ${err.message}</p>`;
    }
}

// --------------------------------------------------------------------------
// Routing & View Switching
// --------------------------------------------------------------------------

function handleRouting() {
    const hash = window.location.hash;
    if (hash.startsWith('#detail/')) {
        const providerId = hash.substring('#detail/'.length);
        showDetail(providerId);
    } else if (hash.startsWith('#detail-')) {
        // Sub-nav anchor (e.g. #detail-basics) — ignore, handled by scrollIntoView
        return;
    } else {
        // Returning from detail view — restore header + tabs first
        const detailSection = document.getElementById('detail-section');
        if (detailSection && !detailSection.classList.contains('hidden')) {
            detailSection.classList.add('hidden');
            document.querySelector('header')?.classList.remove('hidden');
            document.getElementById('view-tabs')?.classList.remove('hidden');
        }
        const tab = hash.substring(1) || 'comparison';
        switchTab(tab, true);
    }
}

function switchTab(tabId, fromRouting = false) {
    // Resolve mainId and subId from the two-level nav structure
    let mainId = tabId;
    let subId = null;

    if (SUB_TO_MAIN[tabId]) {
        // tabId is a sub-tab (e.g. 'comparison', 'radar', 'wallet-types')
        mainId = SUB_TO_MAIN[tabId];
        subId = tabId;
    } else if (NAV_STRUCTURE[tabId]) {
        // tabId is a main tab (e.g. 'overview', 'learn')
        subId = NAV_STRUCTURE[tabId].defaultSub;
    }

    activeTab = subId || mainId;

    if (!fromRouting) {
        window.location.hash = activeTab === 'comparison' ? '' : activeTab;
    }

    // Hide all sections + detail
    document.querySelectorAll('.tab-content').forEach(sec => sec.classList.add('hidden'));
    document.getElementById('detail-section').classList.add('hidden');

    // Show the correct main section
    const activeSection = document.getElementById(`${mainId}-section`);
    if (activeSection) {
        activeSection.classList.remove('hidden');
    }

    // Activate the correct top-level tab button
    document.querySelectorAll('#view-tabs > .tab').forEach(t => {
        t.classList.toggle('active', t.dataset.view === mainId);
    });

    // Handle sub-tab switching within the section
    if (subId && activeSection) {
        activeSection.querySelectorAll('.sub-tab').forEach(t => {
            t.classList.toggle('active', t.dataset.sub === subId);
        });
        activeSection.querySelectorAll('.sub-tab-pane').forEach(p => {
            p.classList.toggle('hidden', p.id !== `${subId}-pane`);
        });
    }

    renderTabContent(activeTab);
}

function showDetail(providerId) {
    const provider = currentData.find(p => p.provider === providerId);
    if (!provider) {
        switchTab('comparison');
        return;
    }

    lastActiveTab = activeTab;
    document.querySelectorAll('.tab-content').forEach(sec => sec.classList.add('hidden'));
    document.getElementById('detail-section').classList.remove('hidden');
    // Hide header + main tabs when in detail view
    document.querySelector('header').classList.add('hidden');
    document.getElementById('view-tabs').classList.add('hidden');
    window.location.hash = `#detail/${providerId}`;

    renderDetail(provider);
}

function closeDetail() {
    document.getElementById('detail-section').classList.add('hidden');
    // Restore header + main tabs
    document.querySelector('header').classList.remove('hidden');
    document.getElementById('view-tabs').classList.remove('hidden');
    switchTab(lastActiveTab);
}

// --------------------------------------------------------------------------
// Main Render Logic
// --------------------------------------------------------------------------

function renderTabContent(tabId) {
    // market tab 独立于 currentData，提前处理
    if (tabId === 'market') {
        loadAndRenderMarketTab();
        return;
    }
    if (!currentData) return;

    switch (tabId) {
        case 'comparison':
            renderComparisonTab(currentData);
            break;
        case 'filter':
            renderFilterTab(currentData);
            break;
        case 'radar':
            renderRadarTab(currentData);
            break;
        case 'latency':
            renderLatencyTab(currentData);
            break;

        case 'wallet-types':
            renderWalletTypesTab();
            break;
        case 'test-design':
            renderMarkdownTab('test-design-container', 'docs/methodology/test-design-philosophy.md');
            break;
        case 'test-detail':
            renderMarkdownTab('test-detail-container', 'docs/methodology/test-item-reference.md');
            break;
        case 'next-steps':
            renderMarkdownTab('next-steps-container', 'docs/next-steps.md');
            break;
    }
}

// --- Tab 1: 功能对比 ---
function renderComparisonTab(providers) {
    renderComparisonCards(providers);
}

function renderComparisonCards(providers) {
    const container = document.getElementById('summary-table-container');
    const sorted = [...providers].sort((a, b) => {
        // Deferred providers always last
        const aDef = DEFERRED_PROVIDERS.includes(a.provider) ? 1 : 0;
        const bDef = DEFERRED_PROVIDERS.includes(b.provider) ? 1 : 0;
        if (aDef !== bDef) return aDef - bDef;
        // Sort by pass rate descending (推荐 first, 不推荐 last)
        const aPct = getPct(a);
        const bPct = getPct(b);
        return bPct - aPct;
    });
    function getPct(p) {
        const results = p.results || [];
        const applicable = results.filter(r => r.status !== 'not_applicable');
        const scorable = applicable.filter(r => r.status !== 'inconclusive' && r.status !== 'skip');
        const passed = scorable.filter(r => r.status === 'pass').length;
        return scorable.length > 0 ? Math.round(passed / scorable.length * 100) : 0;
    }

    let html = '<div class="comparison-grid">';

    for (const p of sorted) {
        const meta = p.provider_meta || {};
        const gov = meta.governance || {};
        const results = p.results || [];
        const applicable = results.filter(r => r.status !== 'not_applicable');
        const scorable = applicable.filter(r => r.status !== 'inconclusive' && r.status !== 'skip');
        const passed = scorable.filter(r => r.status === 'pass').length;
        const scorableTotal = scorable.length;
        const pct = scorableTotal > 0 ? Math.round(passed / scorableTotal * 100) : 0;
        const isDeferred = DEFERRED_PROVIDERS.includes(p.provider);
        const providerColor = PROVIDER_COLORS[p.provider] || '#888';
        // Governance feature tags
        const govFeatures = [];
        if (gov.policy_engine) govFeatures.push('策略引擎');
        if (gov.spend_limit) govFeatures.push('限额');
        if (gov.address_allowlist) govFeatures.push('白名单');
        if (gov.human_in_loop) govFeatures.push('HITL');

        // Chain tags
        const chains = meta.chains || [];
        const mappedChains = [...new Set(chains.map(mapChainName))];

        // Key capabilities — take first 6 from wallet_core category
        const coreCaps = ['key_generate', 'sign_message', 'sign_typed_data', 'send_tx', 'multi_chain', 'preflight_fee'];
        const resultMap = new Map(results.map(r => [r.test_name, r.status]));

        html += `<div class="comp-card${isDeferred ? ' comp-card-deferred' : ''}" data-provider="${p.provider}">`;

        // Header: name + arch badge
        html += `<div class="comp-card-header">`;
        html += `<div class="comp-card-title-row">`;
        html += `<span class="comp-card-name">${meta.name || p.provider}</span>`;
        html += `</div>`;
        html += `<span class="arch-badge ${meta.class || 'unknown'}" title="${ARCH_TOOLTIPS[meta.class] || ARCH_TOOLTIPS.unknown}">${ARCH_LABELS[meta.class] || meta.class || '—'}</span>`;
        html += `</div>`;

        // Verdict badge row
        const verdictLabel = pct >= 80 ? '✅推荐' : pct >= 50 ? '⚠️谨慎' : '❌不推荐';
        const verdictClass = pct >= 80 ? 'verdict-badge-pass' : pct >= 50 ? 'verdict-badge-warn' : 'verdict-badge-fail';
        html += `<div class="comp-card-verdict">`;
        html += `<span class="${verdictClass}">${verdictLabel} ${pct}%</span>`;
        html += `<span class="comp-card-verdict-meta">Key: ${meta.custody_model || '—'} | ${mappedChains.length}链</span>`;
        html += `</div>`;

        // AI insight one-liner
        const insight = AI_INSIGHTS[p.provider];
        if (insight) {
            html += `<div class="comp-card-ai-insight" title="${escapeHtml(insight.body + '\n\n⚠️ 以上洞察基于项目维护者的测试结果撰写，实际数据可能因环境不同而有差异。')}">🤖 ${escapeHtml(insight.title)}</div>`;
        }

        // Core capabilities quick view
        html += `<div class="comp-card-caps">`;
        for (const cap of coreCaps) {
            const status = resultMap.get(cap) || 'not_applicable';
            const label = TEST_NAME_ZH[cap] || cap;
            const icon = STATUS_ICONS[status] || '—';
            html += `<div class="comp-card-cap-item" title="${label}"><span class="comp-card-cap-icon">${icon}</span><span class="comp-card-cap-label">${label}</span></div>`;
        }
        html += `</div>`;

        // DeFi 场景集成
        const defiProvider = decisionData?.providers?.find(dp => dp.id === p.provider);
        if (defiProvider?.defi) {
            const scenarios = defiProvider.defi.scenarios || {};
            const coverage = defiProvider.defi.coverage || '0/0';
            const defiScore = defiProvider.defi.scores?.equal || 0;
            const SCENARIO_NAMES = {
                uniswap_swap: 'Uniswap', aave_morpho: 'Aave/Morpho',
                hyperliquid: 'Hyperliquid', polymarket: 'Polymarket'
            };
            html += `<div class="comp-card-defi">`;
            html += `<div class="comp-card-defi-header">`;
            html += `<span>DeFi 场景集成</span>`;
            html += `<span class="comp-card-defi-coverage">覆盖 ${coverage}</span>`;
            html += `</div>`;
            html += `<div class="comp-card-defi-grid">`;
            for (const [sid, sname] of Object.entries(SCENARIO_NAMES)) {
                const s = scenarios[sid];
                if (s) {
                    html += `<span class="comp-card-defi-item">${s.emoji} ${sname}</span>`;
                }
            }
            html += `</div>`;
            html += `<div class="comp-card-defi-score">DeFi ${defiScore}</div>`;
            html += `</div>`;
        } else {
            html += `<div class="comp-card-defi comp-card-defi-empty"><span>DeFi 场景：暂无数据</span></div>`;
        }

        // Governance tags
        html += `<div class="comp-card-gov">`;
        if (govFeatures.length > 0) {
            govFeatures.forEach(f => {
                html += `<span class="comp-card-gov-tag">${f}</span>`;
            });
        } else {
            html += `<span class="comp-card-gov-empty">无治理功能</span>`;
        }
        html += `</div>`;

        // Bottom accent line
        html += `<div class="comp-card-accent" style="background:${providerColor}"></div>`;

        html += `</div>`; // .comp-card
    }

    html += '</div>'; // .comparison-grid
    container.innerHTML = html;

    // Click to open detail
    container.querySelectorAll('.comp-card').forEach(card => {
        card.addEventListener('click', () => showDetail(card.dataset.provider));
    });
}

// --- Tab 2: 需求筛选 ---
async function renderFilterTab(providers) {
    await loadDecisionData();
    if (decisionData) {
        renderUseCasePresets(decisionData.recommendations, decisionData.providers);
    }
    renderRequirementFilter(providers);
    renderMatrix(providers, decisionData);
    renderMatrixLegend();
}

const USECASE_TO_TESTS = {
    '通用型 AI Agent 钱包': ['key_generate', 'sign_message', 'sign_typed_data', 'send_tx', 'multi_chain', 'token_swap', 'defi_interaction', 'policy_enforcement'],
    '链上 DeFi (Uniswap + Aave)': ['token_swap', 'defi_interaction'],
    'Hyperliquid 永续合约': ['perps_trading', 'sign_typed_data'],
    'Polymarket 预测市场': ['prediction_market', 'sign_typed_data'],
    '企业级风控': ['policy_enforcement', 'session_delegation', 'authorization_audit_trace'],
};

function renderUseCasePresets(recommendations, providers) {
    const container = document.getElementById('usecase-presets');
    if (!container) return;

    const providerMap = new Map(providers.map(p => [p.id, p]));

    let html = '<h4>快速选择场景</h4><div class="usecase-preset-grid">';
    recommendations.forEach(rec => {
        const provider = providerMap.get(rec.recommended);
        if (!provider) return;
        const color = PROVIDER_COLORS[provider.id] || '#888';
        html += `<div class="usecase-preset" data-usecase="${escapeHtml(rec.use_case)}">
            <div class="usecase-preset-title">${escapeHtml(rec.use_case)}</div>
            <div class="usecase-preset-rec"><span class="usecase-preset-swatch" style="background:${color}"></span>推荐 ${escapeHtml(provider.name)}</div>
            <div class="usecase-preset-reason">${escapeHtml(rec.reason)}</div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;

    // Click to auto-select related checkboxes
    container.querySelectorAll('.usecase-preset').forEach(card => {
        card.addEventListener('click', () => {
            const usecase = card.dataset.usecase;
            const testNames = USECASE_TO_TESTS[usecase] || [];
            const isActive = card.classList.contains('active');

            // Deactivate all presets
            container.querySelectorAll('.usecase-preset').forEach(c => c.classList.remove('active'));

            // Clear all checkboxes first
            const filterContainer = document.getElementById('requirement-filter-container');
            filterContainer.querySelectorAll('input:checked').forEach(cb => { cb.checked = false; });

            if (!isActive && testNames.length > 0) {
                card.classList.add('active');
                // Check matching checkboxes by test_name
                filterContainer.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    const testId = cb.dataset.testid;
                    // testId format: "t01_key_generate" → extract test_name after first underscore-number prefix
                    const testName = testId.replace(/^t\d+_/, '');
                    if (testNames.includes(testName)) cb.checked = true;
                });
            }
            // Trigger filter update
            const changeEvent = new Event('change');
            filterContainer.querySelector('input[type="checkbox"]')?.dispatchEvent(changeEvent);
            // Scroll matrix into view
            if (testNames.length > 0) {
                setTimeout(() => {
                    document.getElementById('matrix-container')?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 100);
            }
        });
    });
}

// Identify tests where no provider has a meaningful result (all skip/na/unsupported)
function getUselessTests(providers) {
    const NO_VALUE = new Set(['not_applicable', 'skip', 'unsupported']);
    const testStatuses = new Map();
    providers.forEach(p => p.results.forEach(r => {
        if (!testStatuses.has(r.test_name)) testStatuses.set(r.test_name, []);
        testStatuses.get(r.test_name).push(r.status);
    }));
    const useless = new Set();
    testStatuses.forEach((statuses, name) => {
        if (statuses.every(s => NO_VALUE.has(s))) useless.add(name);
    });
    return useless;
}

function renderRequirementFilter(providers) {
    const container = document.getElementById('requirement-filter-container');
    const uselessTests = getUselessTests(providers);
    const allTests = new Map();
    providers.forEach(p => p.results.forEach(r => {
        if (!allTests.has(r.test_id) && !uselessTests.has(r.test_name)) allTests.set(r.test_id, r.test_name);
    }));
    const sortedTests = [...allTests.entries()].sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }));

    // Group tests by category
    const catGroups = {};
    CATEGORY_META.forEach(c => { catGroups[c.key] = []; });
    sortedTests.forEach(([testId, testName]) => {
        const cat = TEST_CATEGORY[testName] || 'wallet_core';
        if (catGroups[cat]) catGroups[cat].push([testId, testName]);
    });

    let html = '<div class="filter-toolbar"><h4>需求筛选器</h4><div class="filter-toolbar-actions"><span class="filter-count-badge"></span><button class="filter-clear-btn" style="display:none">清除</button></div></div>';
    html += '<div class="filter-category-tabs">';
    html += `<button class="filter-cat-tab active" data-cat="all">全部 (${sortedTests.length})</button>`;
    CATEGORY_META.forEach(c => {
        const count = catGroups[c.key].length;
        if (count > 0) html += `<button class="filter-cat-tab" data-cat="${c.key}">${c.label} (${count})</button>`;
    });
    html += '</div>';
    html += '<div class="filter-group">';
    CATEGORY_META.forEach(c => {
        if (catGroups[c.key].length === 0) return;
        html += `<div class="filter-pill-group" data-cat="${c.key}">`;
        html += `<span class="filter-pill-group-label">${c.label}</span>`;
        catGroups[c.key].forEach(([testId, testName]) => {
            const label = TEST_NAME_ZH[testName] || testName;
            const desc = TEST_DESCRIPTIONS[testName] || '';
            html += `<label class="filter-check-pill" data-cat="${c.key}"${desc ? ` data-tip="${escapeHtml(desc)}"` : ''}><input type="checkbox" data-testid="${testId}"><span>${label}</span></label>`;
        });
        html += '</div>';
    });
    html += '</div>';
    container.innerHTML = html;

    const setCategory = (cat) => {
        container.querySelectorAll('.filter-cat-tab').forEach(btn => btn.classList.toggle('active', btn.dataset.cat === cat));
        container.querySelectorAll('.filter-pill-group').forEach(group => {
            group.style.display = (cat === 'all' || group.dataset.cat === cat) ? '' : 'none';
        });
    };
    container.querySelectorAll('.filter-cat-tab').forEach(btn => {
        btn.addEventListener('click', () => setCategory(btn.dataset.cat));
    });
    setCategory('all');

    const countBadge = container.querySelector('.filter-count-badge');
    const clearBtn = container.querySelector('.filter-clear-btn');

    const updateFilterUI = () => {
        applyRequirementFilter();
        const count = container.querySelectorAll('input:checked').length;
        countBadge.textContent = count > 0 ? `已选 ${count} 项` : '';
        clearBtn.style.display = count > 0 ? '' : 'none';
        // Sync pill active state
        container.querySelectorAll('.filter-check-pill').forEach(lbl => {
            lbl.classList.toggle('active', lbl.querySelector('input').checked);
        });
    };

    container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', updateFilterUI);
    });
    clearBtn.addEventListener('click', () => {
        container.querySelectorAll('input:checked').forEach(cb => { cb.checked = false; });
        updateFilterUI();
        // Also deactivate use case presets
        document.querySelectorAll('#usecase-presets .usecase-preset.active').forEach(el => el.classList.remove('active'));
    });
}

function applyRequirementFilter() {
    const checkedTests = [...document.querySelectorAll('#requirement-filter-container input:checked')]
        .map(cb => cb.dataset.testid);

    const providerHeaders = document.querySelectorAll('#matrix-container .provider-header');

    // Clear all states
    providerHeaders.forEach(th => {
        th.classList.remove('provider-col-grayed', 'provider-col-highlighted');
        const badge = th.querySelector('.filter-match-badge');
        if (badge) badge.remove();
        const colIndex = th.cellIndex;
        document.querySelectorAll(`#matrix-container tr > td:nth-child(${colIndex + 1})`).forEach(td => {
            td.classList.remove('provider-col-grayed', 'provider-col-highlighted');
        });
    });

    if (checkedTests.length === 0) return;

    const providers = currentData.filter(p => !DEFERRED_PROVIDERS.includes(p.provider));
    const providerResults = new Map(providers.map(p => [p.provider, new Map(p.results.map(r => [r.test_id, r]))]));

    // Build DeFi lookup for app-layer match evaluation
    const defiMap = new Map();
    if (decisionData && decisionData.providers) {
        decisionData.providers.forEach(dp => { defiMap.set(dp.id, dp); });
    }
    // Reverse lookup: testId → testName
    const testIdToName = new Map();
    providers.forEach(p => p.results.forEach(r => { testIdToName.set(r.test_id, r.test_name); }));

    providerHeaders.forEach(th => {
        const providerId = th.dataset.provider;
        const results = providerResults.get(providerId);
        if (!results) return;

        const matchCount = checkedTests.filter(testId => {
            const testName = testIdToName.get(testId);
            const scenarioId = testName && TEST_TO_DEFI_SCENARIO[testName];
            if (scenarioId) {
                // For DeFi-mapped tests, count as match if feasible (not "not_feasible")
                const dp = defiMap.get(providerId);
                const scenario = dp?.defi?.scenarios?.[scenarioId];
                return scenario && scenario.rating !== 'not_feasible';
            }
            return results.get(testId)?.status === 'pass';
        }).length;
        const totalCount = checkedTests.length;
        const allMatch = matchCount === totalCount;
        const noneMatch = matchCount === 0;

        th.classList.toggle('provider-col-grayed', !allMatch);
        th.classList.toggle('provider-col-highlighted', allMatch);

        // Add match count badge
        const badgeClass = allMatch ? 'match-all' : noneMatch ? 'match-none' : 'match-partial';
        const badgeText = `${matchCount}/${totalCount}`;
        const badge = document.createElement('span');
        badge.className = `filter-match-badge ${badgeClass}`;
        badge.textContent = badgeText;
        th.appendChild(badge);

        const colIndex = th.cellIndex;
        document.querySelectorAll(`#matrix-container tr > td:nth-child(${colIndex + 1})`).forEach(td => {
            td.classList.toggle('provider-col-grayed', !allMatch);
            td.classList.toggle('provider-col-highlighted', allMatch);
        });
    });

    // Update toolbar badge with match summary
    const matchedCount = [...providerHeaders].filter(th => th.classList.contains('provider-col-highlighted')).length;
    const totalProviders = providerHeaders.length;
    const countBadge = document.querySelector('.filter-count-badge');
    if (countBadge) {
        countBadge.textContent = `已选 ${checkedTests.length} 项 · 符合 ${matchedCount}/${totalProviders} 家`;
    }
}

function renderMatrix(providers, deciData) {
    const container = document.getElementById("matrix-container");
    const activeProviders = providers.filter(p => !DEFERRED_PROVIDERS.includes(p.provider));

    const uselessTests = getUselessTests(activeProviders);
    const allTests = new Map();
    activeProviders.forEach(p => p.results.forEach(r => {
        if (!allTests.has(r.test_id) && !uselessTests.has(r.test_name)) allTests.set(r.test_id, r.test_name);
    }));
    const sortedTests = [...allTests.entries()].sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }));

    // Group tests by category using CATEGORY_META order
    const catGroups = {};
    CATEGORY_META.forEach(c => { catGroups[c.key] = []; });
    sortedTests.forEach(([testId, testName]) => {
        const cat = TEST_CATEGORY[testName] || 'wallet_core';
        if (catGroups[cat]) catGroups[cat].push([testId, testName]);
    });

    // Build result lookup per provider
    const providerResults = new Map(activeProviders.map(p => [p.provider, new Map(p.results.map(r => [r.test_id, r]))]));

    let html = '<div class="table-scroll"><table class="data-table"><thead><tr><th>测试项</th>';
    activeProviders.forEach(p => {
        const meta = p.provider_meta || {};
        const color = PROVIDER_COLORS[p.provider] || '#888';
        html += `<th class="provider-header" data-provider="${p.provider}"><span class="provider-dot" style="background:${color}"></span><span class="provider-name">${meta.name || p.provider}</span></th>`;
    });
    html += '</tr></thead><tbody>';

    function renderRows(tests) {
        for (const [testId, testName] of tests) {
            const label = TEST_NAME_ZH[testName] || testName;
            html += `<tr><td title="${TEST_DESCRIPTIONS[testName] || ''}">${label}</td>`;
            activeProviders.forEach(p => {
                const r = providerResults.get(p.provider)?.get(testId);
                const status = r ? r.status : null;

                let content;
                let cellClass = '';
                let tooltip = '';

                if (status && status !== 'not_applicable') {
                    const icon = STATUS_ICONS[status] || '—';
                    cellClass = STATUS_CLASS[status] || '';
                    content = icon;
                    const msg = r.message ? localizeMessage(r.message) : '';
                    if (msg) tooltip = msg;
                } else if (status === 'not_applicable') {
                    content = '—';
                    cellClass = 'status-na';
                } else {
                    content = '未测试';
                    cellClass = 'status-untested';
                }
                html += `<td class="${cellClass} matrix-cell"${tooltip ? ` data-tip="${escapeHtml(tooltip)}"` : ''}>${content}</td>`;
            });
            html += '</tr>';
        }
    }

    // Build DeFi scenario lookup from decision data
    const defiProviderMap = new Map();
    if (deciData && deciData.providers) {
        deciData.providers.forEach(dp => { defiProviderMap.set(dp.id, dp); });
    }

    CATEGORY_META.forEach(c => {
        if (catGroups[c.key].length === 0) return;
        const headerLabel = (c.key === 'app' && defiProviderMap.size > 0) ? `${c.label} <span class="matrix-group-note">— 集成难度</span>` : c.label;
        html += `<tr class="matrix-group-header"><td>${headerLabel}</td>${'<td></td>'.repeat(activeProviders.length)}</tr>`;

        if (c.key === 'app' && defiProviderMap.size > 0) {
            // Render DeFi difficulty cells instead of pass/fail
            for (const [testId, testName] of catGroups[c.key]) {
                const label = TEST_NAME_ZH[testName] || testName;
                const scenarioId = TEST_TO_DEFI_SCENARIO[testName];
                html += `<tr><td title="${TEST_DESCRIPTIONS[testName] || ''}">${label}</td>`;
                activeProviders.forEach(p => {
                    const dp = defiProviderMap.get(p.provider);
                    const scenario = scenarioId && dp?.defi?.scenarios?.[scenarioId];
                    if (scenario) {
                        const zhLabel = DEFI_RATING_LABEL_ZH[scenario.label] || scenario.label;
                        html += `<td class="defi-difficulty defi-${scenario.rating} matrix-cell"${scenario.rationale ? ` data-tip="${escapeHtml(scenario.rationale)}"` : ''}>${scenario.emoji} ${zhLabel}</td>`;
                    } else {
                        // Fallback to standard rendering if DeFi data missing
                        const r = providerResults.get(p.provider)?.get(testId);
                        const status = r ? r.status : null;
                        if (status && status !== 'not_applicable') {
                            const icon = STATUS_ICONS[status] || '—';
                            html += `<td class="${STATUS_CLASS[status] || ''}">${icon}</td>`;
                        } else if (status === 'not_applicable') {
                            html += `<td class="status-na">—</td>`;
                        } else {
                            html += `<td class="status-untested">未测试</td>`;
                        }
                    }
                });
                html += '</tr>';
            }
        } else {
            renderRows(catGroups[c.key]);
        }
    });

    html += '</tbody></table></div>';

    // Inline legend above table
    const legendHtml = `<div class="matrix-inline-legend">${STATUS_ICONS.pass} 通过 ${STATUS_ICONS.fail} 失败 ${STATUS_ICONS.unsupported} 不支持 ${STATUS_ICONS.inconclusive} 待确认 ${STATUS_ICONS.skip} 行业缺口 <span class="status-na">N/A</span><span class="matrix-legend-sep">|</span>🟢 即用 🟡 低门槛 🟠 中等 🔴 不可行</div>`;
    container.innerHTML = legendHtml + html;

    container.querySelectorAll('.provider-header').forEach(th => {
        th.addEventListener('click', () => showDetail(th.dataset.provider));
    });
}

function renderMatrixLegend() {
    // Legend is now rendered inline inside renderMatrix — this is a no-op for backward compat
}


// --- Tab 2: 能力雷达 ---
const RADAR_DIMENSIONS = [
    { key: 'wallet_core', label: '钱包基础',
      desc: '钱包基础功能通过率：创建钱包、签名、转账、多链、Gas 预估等。公式：pass ÷ (pass + fail) × 100。' },
    { key: 'governance', label: '权限治理',
      desc: '策略引擎、临时授权、审计追踪的通过率（权重 60%）+ 治理完整度 YAML 评分（权重 40%）。' },
    { key: 'reliability', label: '稳定性',
      desc: '并发处理、故障恢复、限流韧性的通过率。公式：pass ÷ (pass + fail) × 100。' },
    { key: 'ops', label: '运维能力',
      desc: '运维类测试通过率（权重 50%）+ 环境矩阵和文档上手度 YAML 评分均值（权重 50%）。' },
    { key: 'app', label: '应用能力',
      desc: 'DeFi 对接能力：基于 4 场景（Uniswap Swap / Aave 借贷 / Hyperliquid 永续 / Polymarket 预测市场）的对接成本评伌，等权平均。数据来源：DeFi Integration Cost Matrix v1。' },
    { key: 'security', label: '安全性',
      desc: '签名验证、密钥轮换等安全测试通过率。公式：pass ÷ (pass + fail + error + unsupported) × 100。' },
    { key: 'agent', label: 'Agent 可用性',
      desc: 'AI Agent 集成质量：返回结构完整性、错误可机读性、响应确定性的通过率。公式：pass ÷ (pass + fail + error + unsupported) × 100。' },
      desc: 'DeFi 对接能力：基于 4 场景（Uniswap Swap / Aave 借贷 / Hyperliquid 永续 / Polymarket 预测市场）的对接成本评估，等权平均。数据来源：DeFi Integration Cost Matrix v1。' },
];

async function renderRadarTab(providers) {
    const activeProviders = providers.filter(p => !DEFERRED_PROVIDERS.includes(p.provider));
    renderRadarToggle(activeProviders);
    renderMainRadarChart(activeProviders);
    renderRadarLegend(activeProviders);
    // DeFi heatmap below radar chart
    await loadDecisionData();
    if (decisionData) {
        renderDefiHeatmap(decisionData.providers, decisionData.scenarios, decisionData.rating_definitions, 'radar-defi-heatmap');
    }
}

function renderRadarLegend(providers) {
    const container = document.getElementById('radar-legend');

    // Provider ranking by pass rate
    const ranked = providers.map(p => {
        const results = getApplicableResults(p);
        const scorable = results.filter(r => r.status !== 'inconclusive' && r.status !== 'skip');
        const passed = scorable.filter(r => r.status === 'pass').length;
        const total = scorable.length;
        const pct = total > 0 ? Math.round(passed / total * 100) : 0;
        const radarScores = computeRadarScores(p);
        const overall = Math.round(RADAR_DIMENSIONS.reduce((sum, d) => sum + radarScores[d.key], 0) / RADAR_DIMENSIONS.length);
        return { provider: p, name: p.provider_meta?.name || p.provider, pct, passed, total, overall };
    }).sort((a, b) => b.pct - a.pct);

    let html = '<h3>综合排名</h3>';
    html += '<div class="radar-rank-list">';
    ranked.forEach((r, i) => {
        const color = PROVIDER_COLORS[r.provider.provider] || '#888';
        const verdictClass = r.pct >= 80 ? 'rank-pass' : r.pct >= 50 ? 'rank-warn' : 'rank-fail';
        html += `<div class="radar-rank-item ${verdictClass}" data-provider="${r.provider.provider}">
            <span class="radar-rank-pos">#${i + 1}</span>
            <span class="radar-rank-swatch" style="background:${color}"></span>
            <span class="radar-rank-name">${r.name}</span>
            <span class="radar-rank-score">${r.pct}%</span>
            <span class="radar-rank-detail">${r.passed}/${r.total} 通过 · 综合 ${r.overall}</span>
        </div>`;
    });
    html += '</div>';

    // Dimension descriptions (collapsed)
    html += '<details class="radar-dim-details"><summary>维度说明</summary>';
    html += RADAR_DIMENSIONS.map(d =>
        `<div class="radar-legend-item"><span class="radar-legend-label">${d.label}</span><span class="radar-legend-desc">${d.desc}</span></div>`
    ).join('');
    html += '</details>';

    container.innerHTML = html;

    // Click to open detail
    container.querySelectorAll('.radar-rank-item').forEach(el => {
        el.style.cursor = 'pointer';
        el.addEventListener('click', () => showDetail(el.dataset.provider));
    });
}

function renderRadarToggle(providers) {
    const container = document.getElementById('radar-toggle-container');
    let html = '';
    providers.forEach(p => {
        const color = PROVIDER_COLORS[p.provider] || getCssVar('--text-tertiary');
        html += `<label>
            <input type="checkbox" data-provider="${p.provider}" checked>
            <span class="color-swatch" style="background-color: ${color}"></span>
            <span>${p.provider_meta?.name || p.provider}</span>
        </label>`;
    });
    container.innerHTML = html;
    container.querySelectorAll('input').forEach(checkbox => {
        checkbox.addEventListener('change', updateRadarVisibility);
    });
}

function computeRadarScores(provider) {
    const results = getApplicableResults(provider);
    const allResults = provider.results || [];
    const ev = provider.evaluation || {};
    const scores = ev.scores || {};

    // Helper: pass rate for a category
    // Scorable = pass + fail + error + unsupported (provider responsibility)
    // Excluded from denominator: skip (industry blank), inconclusive (benchmark gap), not_applicable (arch mismatch)
    function catPassRate(catKey) {
        const catResults = results.filter(r => TEST_CATEGORY[r.test_name] === catKey);
        const passed = catResults.filter(r => r.status === 'pass').length;
        const scorable = catResults.filter(r =>
            r.status === 'pass' || r.status === 'fail' || r.status === 'error' || r.status === 'unsupported'
        ).length;
        return scorable > 0 ? (passed / scorable) * 100 : 0;
    }

    // Helper: YAML score (1-5 normal scale) to percentage (5 = 100)
    function yamlPct(field) {
        const val = scores[field];
        return (val != null && val > 0) ? val * 20 : null;
    }

    // Helper: weighted blend of auto pass rate + yaml percentage
    function blend(autoRate, yamlFields, autoWeight) {
        const yamlVals = yamlFields.map(yamlPct).filter(v => v !== null);
        if (yamlVals.length === 0) return autoRate;
        const yamlAvg = yamlVals.reduce((a, b) => a + b, 0) / yamlVals.length;
        return autoRate * autoWeight + yamlAvg * (1 - autoWeight);
    }

    const wallet_core = catPassRate('wallet_core');
    const governance = blend(catPassRate('governance'), ['governance_completeness'], 0.6);
    const reliability = catPassRate('reliability');
    const ops = blend(catPassRate('ops'), ['network_environment', 'sdk_doc_quality'], 0.5);
    const security = catPassRate('security');
    const agent = catPassRate('agent');
    // App dimension: use DeFi matrix equal-weight score if available, fallback to old test pass rate
    let app;
    const providerId = provider.provider;
    const defiProvider = decisionData?.providers?.find(p => p.id === providerId);
    if (defiProvider?.defi?.scores?.equal != null) {
        app = defiProvider.defi.scores.equal;  // already 0-100 scale
    } else {
        app = blend(catPassRate('app'), ['app_tool_coverage', 'app_execution_quality'], 0.5);
    }

    return {
        wallet_core, governance, reliability, ops, app, security, agent,
        _applicableCount: results.length,
        _totalCount: allResults.length
    };
}


function renderMainRadarChart(providers) {
    const container = document.getElementById('radar-container');
    container.innerHTML = '<canvas id="main-radar-chart"></canvas>';
    const ctx = document.getElementById('main-radar-chart').getContext('2d');

    const labels = RADAR_DIMENSIONS.map(d => d.label);
    const keys = RADAR_DIMENSIONS.map(d => d.key);

    const datasets = providers.map(p => {
        const scores = computeRadarScores(p);
        const color = PROVIDER_COLORS[p.provider] || getCssVar('--text-tertiary');
        return {
            label: p.provider_meta?.name || p.provider,
            data: keys.map(key => scores[key]),
            borderColor: color,
            backgroundColor: `${color}22`,
            pointBackgroundColor: color,
            borderWidth: 2.5,
            pointRadius: 4,
            pointHoverRadius: 6,
            hidden: false,
            _provider: p.provider
        };
    });

    if (mainRadarChart) {
        mainRadarChart.destroy();
    }

    mainRadarChart = new Chart(ctx, {
        type: 'radar',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: { mode: 'nearest', intersect: true },
            scales: {
                r: {
                    angleLines: { color: getCssVar('--bg-border') },
                    grid: { color: getCssVar('--bg-border') },
                    pointLabels: { color: getCssVar('--text-secondary'), font: { size: 12 } },
                    ticks: { display: false, backdropColor: 'transparent' },
                    suggestedMin: 0,
                    suggestedMax: 100,
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.r !== null) {
                                label += context.parsed.r.toFixed(2);
                            }
                            return label;
                        }
                    }
                }
            },
            onClick: (_evt, elements) => {
                if (elements.length > 0) {
                    const datasetIndex = elements[0].datasetIndex;
                    const providerId = mainRadarChart.data.datasets[datasetIndex]._provider;
                    showDetail(providerId);
                }
            }
        }
    });
}

function updateRadarVisibility() {
    if (!mainRadarChart) return;
    const checkboxes = document.querySelectorAll('#radar-toggle-container input');
    checkboxes.forEach(checkbox => {
        const providerId = checkbox.dataset.provider;
        const datasetIndex = mainRadarChart.data.datasets.findIndex(d => d._provider === providerId);
        if (datasetIndex !== -1) {
            mainRadarChart.setDatasetVisibility(datasetIndex, checkbox.checked);
        }
    });
    mainRadarChart.update();
}

// --- Tab 3: 延迟分析 ---
function renderLatencyTab(providers) {
    const activeProviders = providers.filter(p => !DEFERRED_PROVIDERS.includes(p.provider));
    renderLatencyDisclaimer();
    renderHeatmapStats(activeProviders);
    renderHeatmap(activeProviders);
}

function renderLatencyDisclaimer() {
    const section = document.getElementById('latency-pane');
    // Avoid duplicate
    if (section.querySelector('.latency-env-disclaimer')) return;
    const div = document.createElement('div');
    div.className = 'latency-env-disclaimer';
    div.innerHTML =
        '<strong>⚠️ 免责声明</strong>' +
        '<p>以下延迟数据仅代表本项目维护者在特定本地网络环境下的测试结果，<strong>不构成通用性能基准</strong>。' +
        '不同地域、网络运营商、API 密钥配额及服务器负载均会显著影响实际延迟。</p>' +
        '<p>建议您克隆本项目后，配置自己的 API Key / 钱包凭证，在自身网络环境中重新运行 <code>python runner.py</code> 以获取贴合实际场景的数据。</p>';
    section.insertBefore(div, section.firstChild);
}

function renderHeatmapStats(providers) {
    const container = document.getElementById('heatmap-stats-container');
    let html = '';
    for (const p of providers) {
        const latencies = p.results.filter(r => getLatencyMs(r) > 0).map(r => getLatencyMs(r));
        if (latencies.length === 0) continue;
        const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;
        const max = Math.max(...latencies);
        const min = Math.min(...latencies);
        const name = p.provider_meta?.name || p.provider;
        const color = PROVIDER_COLORS[p.provider] || getCssVar('--text-tertiary');

        html += `<div class="heatmap-stat-card">
            <div class="stat-label" style="color:${color}">${name}</div>
            <div class="stat-value">${avg.toFixed(0)}ms</div>
            <div class="stat-label">均值 (${min.toFixed(0)}-${max.toFixed(0)}ms)</div>
        </div>`;
    }
    container.innerHTML = html;
}

function latencyColor(ms) {
    if (ms <= 0) return "transparent";
    const log = Math.log10(Math.max(1, ms));
    const t = Math.min(1, Math.max(0, (log - 1) / 3));
    if (t < 0.4) return `hsl(160, 60%, ${35 + (1-t)*10}%)`;
    if (t < 0.7) return `hsl(45, 80%, ${45 + (0.7-t)*10}%)`;
    return `hsl(0, 70%, ${45 + (1-t)*10}%)`;
}

function renderHeatmap(providers) {
    const container = document.getElementById("heatmap-container");
    const allTests = new Map();
    providers.forEach(p => p.results.forEach(r => {
        if (!allTests.has(r.test_id)) allTests.set(r.test_id, r.test_name);
    }));
    const sortedTests = [...allTests.entries()].sort((a, b) => a[0].localeCompare(b[0], undefined, { numeric: true }));
    const lookup = new Map(providers.map(p => [p.provider, new Map(p.results.map(r => [r.test_id, r]))]));

    let html = '<div class="latency-legend">';
    html += '<span class="latency-legend-title">延迟阈值:</span>';
    html += '<span class="latency-legend-item"><span class="latency-legend-dot" style="background:hsl(160,60%,40%)"></span>&lt; 500ms</span>';
    html += '<span class="latency-legend-item"><span class="latency-legend-dot" style="background:hsl(45,80%,45%)"></span>500 – 2000ms</span>';
    html += '<span class="latency-legend-item"><span class="latency-legend-dot" style="background:hsl(0,70%,45%)"></span>&gt; 2000ms</span>';
    html += '</div>';

    html += '<div class="table-scroll"><table class="heatmap-table"><thead><tr><th>测试项</th>';
    providers.forEach(p => {
        html += `<th>${p.provider_meta?.name || p.provider}</th>`;
    });
    html += '</tr></thead><tbody>';

    for (const [testId, testName] of sortedTests) {
        html += `<tr><td>${TEST_NAME_ZH[testName] || testName}</td>`;
        for (const p of providers) {
            const r = lookup.get(p.provider)?.get(testId);
            if (r && getLatencyMs(r) > 0) {
                const ms = getLatencyMs(r);
                const bg = latencyColor(ms);
                const textColor = getCssVar('--text-primary');
                html += `<td><span class="heatmap-cell" style="background:${bg};color:${textColor}">${ms.toFixed(0)}ms</span></td>`;
            } else {
                html += `<td><span class="heatmap-cell-empty">—</span></td>`;
            }
        }
        html += '</tr>';
    }
    html += '</tbody></table></div>';
    html += '<div class="heatmap-scale"><span>快 (&lt;100ms)</span><div class="heatmap-scale-bar"></div><span>慢 (&gt;10s)</span></div>';
    // AC-003-27: Show disclaimer if any result has multi-run latency data
    const hasMultiRun = providers.some(p => p.results.some(r => r.latency && r.latency.runs_count > 1));
    if (hasMultiRun) {
        const maxRuns = Math.max(...providers.flatMap(p => p.results.filter(r => r.latency).map(r => r.latency.runs_count)));
        html += `<p class="heatmap-disclaimer">⚠️ 数据基于 ${maxRuns} 次测试的中位数，已排除失败样本</p>`;
    }

    container.innerHTML = html;
}


// --- Decision data (used by radar & filter tabs) ---

async function loadDecisionData() {
    if (decisionData) return;
    try {
        const resp = await fetch("data/decision_view.v1.json");
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        decisionData = await resp.json();
    } catch (err) {
        decisionData = { providers: [], scenarios: [], weight_presets: {}, rating_definitions: {}, recommendations: [] };
    }
}

function renderDefiHeatmap(providers, scenarios, _ratingDefs, containerId = 'decision-heatmap') {
    const container = document.getElementById(containerId);
    if (!container) return;

    // Use top-level DEFI_SCENARIO_NAME_ZH and DEFI_RATING_LABEL_ZH

    const sortedProviders = [...providers].sort((a, b) => (b.defi?.scores?.equal || 0) - (a.defi?.scores?.equal || 0));

    let html = '<h3>DeFi 场景 Agent 集成难度</h3>';
    html += '<div class="table-scroll"><table class="data-table"><thead><tr><th>服务商</th>';
    scenarios.forEach(s => {
        html += `<th>${DEFI_SCENARIO_NAME_ZH[s.name] || s.name}</th>`;
    });
    html += '<th>覆盖率</th><th>DeFi 分</th></tr></thead><tbody>';

    sortedProviders.forEach(p => {
        const providerColor = PROVIDER_COLORS[p.id] || '#888';
        html += `<tr><td><a class="defi-provider-link" data-provider="${p.id}" style="color:${providerColor}; font-weight:600; cursor:pointer;">${p.name}</a></td>`;
        const defiInfo = p.defi || { scenarios: {} };

        scenarios.forEach(s => {
            const scenarioData = defiInfo.scenarios[s.id];
            if (scenarioData) {
                const labelZh = DEFI_RATING_LABEL_ZH[scenarioData.label] || scenarioData.label;
                html += `<td class="defi-${scenarioData.rating}">${scenarioData.emoji} ${labelZh}</td>`;
            } else {
                html += `<td class="defi-not-feasible">🚫 不可行</td>`;
            }
        });

        html += `<td>${defiInfo.coverage || '0/0'}</td>`;
        html += `<td>${(p.defi?.scores?.equal || 0).toFixed(1)}</td>`;

        html += '</tr>';
    });

    html += '</tbody></table></div>';
    container.innerHTML = html;

    container.querySelectorAll('.defi-provider-link').forEach(el => {
        el.addEventListener('click', () => showDetail(el.dataset.provider));
    });
}



// --------------------------------------------------------------------------
// Detail Page Rendering
// --------------------------------------------------------------------------

function renderDecisionBar(provider) {
    const barEl = document.getElementById('detail-decision-bar');
    const results = getApplicableResults(provider);
    if (!results.length) {
        barEl.innerHTML = '<div class="decision-bar"><span class="decision-empty">暂无适用测试数据</span></div>';
        return;
    }
    const total = results.length;
    const inconclusiveCount = results.filter(r => r.status === 'inconclusive').length;
    const scorable = results.filter(r => r.status !== 'inconclusive' && r.status !== 'skip');
    const passed = scorable.filter(r => r.status === 'pass').length;
    const scorableTotal = scorable.length;
    const rate = scorableTotal > 0 ? Math.round((passed / scorableTotal) * 100) : 0;
    const confidence = total > 0 ? Math.round(((total - inconclusiveCount) / total) * 100) : 100;
    
    let verdict, verdictColor, verdictClass, verdictIcon;
    if (rate >= 80) { verdict = '推荐'; verdictColor = 'var(--color-pass)'; verdictClass = 'verdict-pass'; verdictIcon = '✅'; }
    else if (rate >= 50) { verdict = '谨慎'; verdictColor = 'var(--color-skip)'; verdictClass = 'verdict-warn'; verdictIcon = '⚠️'; }
    else { verdict = '不推荐'; verdictColor = 'var(--color-fail)'; verdictClass = 'verdict-fail'; verdictIcon = '🚫'; }
    
    // p50 latency
    const latencies = results.filter(r => getLatencyMs(r) > 0).map(r => getLatencyMs(r)).sort((a, b) => a - b);
    const p50 = latencies.length > 0 ? latencies[Math.floor(latencies.length / 2)] : null;
    
    // Top blocker — only show app / wallet_core failures; deeper issues belong in test detail table
    const BLOCKER_CATS = new Set(['app', 'wallet_core']);
    const userFacingFailures = results.filter(r =>
        (r.status === 'fail' || r.status === 'error') && BLOCKER_CATS.has(TEST_CATEGORY[r.test_name])
    );
    const blocker = userFacingFailures[0] || null;
    
    let html = `<div class="decision-bar ${verdictClass}">`;
    html += `<span class="decision-verdict" style="background:${verdictColor};color:var(--bg-base)">${verdictIcon} ${verdict}</span>`;
    const naCount = (provider.results || []).filter(r => r.status === 'not_applicable').length;
    const excludedCount = total - scorableTotal;
    const excludedTip = naCount > 0 ? `${naCount} 项不适用` : '';
    const incTip = inconclusiveCount > 0 ? `${inconclusiveCount} 项无定论` : '';
    const excludedParts = [excludedTip, incTip].filter(Boolean).join('，');
    const excludedLabel = excludedParts ? `（${excludedParts}不计入）` : '';
    html += `<span class="decision-stat" title="共 ${total + naCount} 项测试，${excludedCount + naCount} 项未计入评分">${passed}/${scorableTotal} 通过 ${rate}%<span class="decision-stat-note">${excludedLabel}</span></span>`;
    html += `<span class="confidence-badge">置信度 <span class="conf-value">${confidence}%</span></span>`;
    html += `<span class="decision-stat" title="中位延迟（第50百分位）">p50: ${p50 ? Math.round(p50) + 'ms' : '—'}</span>`;
    if (blocker) {
        const blockerName = TEST_NAME_ZH[blocker.test_name] || blocker.test_name;
        const blockerVerb = blocker.status === 'error' ? '异常' : '未通过';
        html += `<span class="decision-stat decision-blocker">${blockerName} ${blockerVerb}</span>`;
    }
    html += '</div>';
    barEl.innerHTML = html;
}

function renderScoreCard(provider) {
    const scores = computeRadarScores(provider);

    const dims = RADAR_DIMENSIONS.map(d => ({ key: d.key, label: d.label }));
    const total = Math.round(dims.reduce((sum, d) => sum + scores[d.key], 0) / dims.length);
    function semanticColor(val) {
        if (val >= 80) return 'var(--color-pass)';
        if (val >= 50) return 'var(--color-skip)';
        return 'var(--color-fail)';
    }
    let html = '<div class="detail-card wide score-card">';
    html += '<div class="score-card-header">';
    html += `<div class="score-card-total" style="color:${semanticColor(total)}">${total}<span class="score-card-unit">/100</span></div>`;
    html += '<canvas id="detail-score-radar" width="200" height="200"></canvas>';
    html += '</div>';
    html += '<div class="score-card-body">';
    html += '<h3>综合评分</h3>';
    html += '<div class="score-card-dims">';
    for (const d of dims) {
        const val = Math.round(scores[d.key]);
        const color = semanticColor(val);
        const dimDesc = RADAR_DIMENSIONS.find(dim => dim.key === d.key)?.desc || '';
        html += `<div class="score-card-row">
            <span class="score-card-label" title="${escapeHtml(dimDesc)}">${d.label}</span>
            <div class="score-card-bar"><div class="score-card-fill" style="width:${val}%;background:${color}"></div></div>
            <span class="score-card-val">${val}%</span>
        </div>`;
    }
    html += '</div>';
    html += `<div class="score-card-applicable">基于 ${scores._applicableCount}/${scores._totalCount} 适用测试</div>`;
    html += '</div>';
    html += '</div>';
    return html;
}

function renderDetailDefiCard(providerId) {
    const dp = decisionData?.providers?.find(p => p.id === providerId);
    if (!dp?.defi?.scenarios) return '';
    const scenarios = decisionData.scenarios || [];
    const defi = dp.defi;

    let rows = '';
    scenarios.forEach(s => {
        const sc = defi.scenarios[s.id];
        if (!sc) return;
        const name = DEFI_SCENARIO_NAME_ZH[s.name] || s.name;
        const chain = s.chain || '';
        const ratingClass = 'defi-detail-' + sc.rating;
        rows += `<tr class="${ratingClass}">
            <td class="defi-detail-scenario">${name}<span class="defi-detail-chain">${chain}</span></td>
            <td class="defi-detail-rating">${sc.emoji} ${sc.label}</td>
            <td class="defi-detail-rationale">${escapeHtml(sc.rationale)}</td>
        </tr>`;
    });

    const score = Math.round(defi.scores?.equal ?? 0);
    const coverage = defi.coverage || '—';
    const color = score >= 80 ? 'var(--color-pass)' : score >= 50 ? 'var(--color-skip)' : 'var(--color-fail)';

    let html = `<div class="detail-card wide detail-defi-card">`;
    html += `<h3>DeFi 场景集成能力</h3>`;
    html += `<div class="defi-detail-summary">`;
    html += `<span class="defi-detail-score" style="color:${color}">${score}<span class="score-card-unit">/100</span></span>`;
    html += `<span class="defi-detail-coverage">覆盖 ${coverage} 场景</span>`;
    html += `</div>`;
    html += `<div class="table-scroll"><table class="defi-detail-table"><thead><tr><th>场景</th><th>评级</th><th>说明</th></tr></thead><tbody>${rows}</tbody></table></div>`;
    html += `</div>`;
    return html;
}

function renderDetail(provider) {
    renderDecisionBar(provider);
    const nameContainer = document.getElementById('detail-provider-name');
    const container = document.getElementById('detail-container');
    
    const meta = provider.provider_meta || {};
    const caps = provider.capabilities || {};
    nameContainer.textContent = meta.name || provider.provider;

    // Sub-nav visibility
    const detailNav = document.getElementById('detail-nav');
    const evalLink = detailNav.querySelector('a[href="#detail-eval"]');
    const memoLink = detailNav.querySelector('a[href="#detail-memo"]');
    if (evalLink) evalLink.style.display = provider.evaluation ? '' : 'none';
    if (memoLink) memoLink.style.display = (provider.evaluation?.agent_memo || provider.evaluation?.agent_experience) ? '' : 'none';

    let html = '';
    // AC-005-12 Deferred Banner
    if (DEFERRED_PROVIDERS.includes(provider.provider)) {
        html += '<div class="detail-provider-banner">此服务商已被标记为 DEFERRED，以下数据仅供参考。</div>';
    }

    html += '<div class="detail-tab-pane" id="detail-basics">';
    // AI Insight block (replaces old evaluation summary)
    const aiInsight = AI_INSIGHTS[provider.provider];
    if (aiInsight) {
        html += `<div class="detail-ai-insight">`;
        html += `<div class="detail-ai-insight-header">🤖 AI 洞察</div>`;
        html += `<div class="detail-ai-insight-title">${escapeHtml(aiInsight.title)}</div>`;
        html += `<div class="detail-ai-insight-body">${escapeHtml(aiInsight.body)}</div>`;
        html += `<div class="detail-ai-insight-disclaimer">以上洞察基于项目维护者的测试结果撰写，若你自行运行测试，实际延迟和通过率可能因网络环境及 API 版本不同而有差异。</div>`;
        html += `</div>`;
    }
    html += '<div class="detail-grid">';
    html += renderScoreCard(provider);
    html += renderDetailDefiCard(provider.provider);
    if (meta.takeaways) {
        let takeawaysHtml = '';
        if (meta.takeaways.learn) {
            takeawaysHtml += `<div class="takeaway-item takeaway-learn">
                <span class="takeaway-icon">💡</span>
                <div>
                    <div class="takeaway-label">可借鉴</div>
                    <div class="takeaway-text">${escapeHtml(sanitizeText(meta.takeaways.learn))}</div>
                </div>
            </div>`;
        }
        if (meta.takeaways.avoid) {
            takeawaysHtml += `<div class="takeaway-item takeaway-avoid">
                <span class="takeaway-icon">⚠️</span>
                <div>
                    <div class="takeaway-label">应规避</div>
                    <div class="takeaway-text">${escapeHtml(sanitizeText(meta.takeaways.avoid))}</div>
                </div>
            </div>`;
        }
        html += renderDetailCard('关键要点', takeawaysHtml);
    }
    html += renderDetailCard('架构信息', `
        <p><strong>类别:</strong> <span class="arch-badge ${meta.class || 'unknown'}" title="${ARCH_TOOLTIPS[meta.class] || ARCH_TOOLTIPS.unknown}">${ARCH_LABELS[meta.class] || meta.class || '—'}</span></p>
        <p><strong>Key 托管:</strong> ${meta.custody_description || mapTechField(meta.custody_model) || '—'}</p>
        <p><strong>提交方式:</strong> ${mapTechField(meta.submission_mode) || '—'}</p>
    `);
    const chainTags = (meta.chains || []).map(c => `<span class="tag">${mapChainName(c)}</span>`).join(' ') || '—';
    const sigTags = (meta.signing_modes || []).map(m => `<span class="tag" title="${escapeHtml(SIGNING_MODE_DESC[m] || '')}">${mapTechField(m)}</span>`).join(' ') || '—';
    html += renderDetailCard('链与签名', `
        <p><strong>支持链:</strong> ${chainTags}</p>
        <p><strong>签名方式:</strong> ${sigTags}</p>
    `);
    const resultMap = new Map((provider.results || []).map(r => [r.test_name, r]));
    const capHtml = Object.entries(caps).map(([k]) => {
        const testName = CAP_TO_TEST[k];
        const testResult = testName ? resultMap.get(testName) : null;
        const testStatus = testResult?.status || null;
        let borderColor = 'var(--bg-border)';
        let opacity = 1;
        if (testStatus === 'pass') borderColor = 'var(--color-pass)';
        else if (testStatus === 'fail' || testStatus === 'error') borderColor = 'var(--color-fail)';
        else if (testStatus === 'unsupported') borderColor = 'var(--color-unsupported)';
        else if (testStatus === 'inconclusive') borderColor = 'var(--color-inconclusive)';
        else if (testStatus === 'skip') borderColor = 'var(--color-skip)';
        else if (testStatus === 'not_applicable') { borderColor = 'var(--text-tertiary)'; opacity = 0.5; }
        const label = CAP_NAME_ZH[k] || TEST_NAME_ZH[k] || k;
        let desc;
        if (testStatus === 'not_applicable') {
            const skipReason = testResult?.skip_reason || testResult?.message || '';
            if (skipReason === 'category_mismatch' || skipReason.includes('无内置应用层')) {
                desc = '无内置 API，可通过 send_transaction + calldata 实现。详见 DeFi 集成矩阵';
            } else if (skipReason === 'architecture_mismatch') {
                desc = '该测试仅适用于 local 架构的供应商';
            } else {
                desc = '该能力不在此服务商产品定位范围内';
            }
        } else {
            desc = testName ? TEST_DESCRIPTIONS[testName] : null;
        }
        const tooltip = desc ? `${label} — ${desc}` : label;
        return `<span class="tag" style="border-color:${borderColor};opacity:${opacity}" title="${escapeHtml(tooltip)}">${label}</span>`;
    }).join(' ');
    html += `<div class="detail-card wide"><h3>能力清单</h3><div>${capHtml || '—'}</div></div>`;

    // Agent Skill 集成信息
    const skill = meta.skill || {};
    if (meta.skill) {
        const color = PROVIDER_COLORS[provider.provider] || getCssVar('--text-tertiary');
        let skillHtml = '';
        if (skill.description) {
            skillHtml += `<p class="skill-desc">${escapeHtml(sanitizeText(skill.description))}</p>`;
        }

        // Top row: package + integration type + copy
        skillHtml += '<div class="skill-top-row">';
        if (skill.package) {
            const pkgText = `${skill.package}`;
            skillHtml += `<code class="skill-pkg">${escapeHtml(pkgText)}</code>`;
            skillHtml += `<button class="copy-btn copy-btn-inline" onclick="copyText(this, '${escapeHtml(pkgText)}')">复制</button>`;
        }
        if (skill.integration_type) {
            skillHtml += `<span class="integration-badge">${escapeHtml(skill.integration_type)}</span>`;
        }
        skillHtml += '</div>';

        // Meta grid: stars, license, verified, registry
        const metaItems = [];
        if (skill.package_registry) metaItems.push(['Registry', skill.package_registry]);
        if (skill.stars) metaItems.push(['Stars', String(skill.stars)]);
        if (skill.license) metaItems.push(['License', skill.license]);
        if (skill.last_verified) metaItems.push(['验证', skill.last_verified]);
        if (metaItems.length > 0) {
            skillHtml += '<div class="skill-meta-chips">';
            metaItems.forEach(([label, value]) => {
                skillHtml += `<span class="skill-chip"><span class="skill-chip-label">${label}</span>${escapeHtml(value)}</span>`;
            });
            skillHtml += '</div>';
        }

        // Links row
        const links = [];
        if (skill.github) links.push(['GitHub', skill.github]);
        if (skill.docs_url) links.push(['文档', skill.docs_url]);
        if (links.length > 0) {
            skillHtml += '<div class="skill-links">';
            links.forEach(([label, url]) => {
                skillHtml += `<a href="${escapeHtml(url)}" target="_blank" rel="noopener" class="skill-link-btn">${label} ↗</a>`;
            });
            if (skill.integration_type) {
                skillHtml += `<a href="integration-types.html" class="skill-link-btn skill-link-muted">集成方式对比 →</a>`;
            }
            skillHtml += '</div>';
        }

        html += `<div class="detail-card wide skill-card" style="border-left:3px solid ${color}"><h3>Agent Skill 集成信息</h3>${skillHtml}</div>`;
    }

    html += '</div>'; // .detail-grid
    html += '</div>'; // #detail-basics

    // ========== Tab 2: 测试结果 ==========
    html += '<div class="detail-tab-pane hidden" id="detail-tests">';
    const STATUS_ORDER = { fail: 0, error: 1, unsupported: 2, inconclusive: 3, skip: 4, pass: 5, not_applicable: 6 };
    const sortedResults = [...provider.results].sort((a, b) => {
        const sa = STATUS_ORDER[a.status] ?? 99;
        const sb = STATUS_ORDER[b.status] ?? 99;
        if (sa !== sb) return sa - sb;
        return (getLatencyMs(b)) - (getLatencyMs(a));
    });
    const counts = { all: sortedResults.length, fail: 0, skip: 0, pass: 0, not_applicable: 0, unsupported: 0, inconclusive: 0 };
    sortedResults.forEach(r => { if (counts[r.status] !== undefined) counts[r.status]++; });
    counts.fail += sortedResults.filter(r => r.status === 'error').length;
    html += '<div class="test-filter-pills">';
    html += `<button class="filter-pill active" data-filter="all">全部 (${counts.all})</button>`;
    html += `<button class="filter-pill" data-filter="fail" ${counts.fail === 0 ? 'disabled' : ''}>失败 (${counts.fail})</button>`;
    html += `<button class="filter-pill" data-filter="unsupported" ${counts.unsupported === 0 ? 'disabled' : ''}>不支持 (${counts.unsupported})</button>`;
    html += `<button class="filter-pill" data-filter="inconclusive" ${counts.inconclusive === 0 ? 'disabled' : ''}>待确认 (${counts.inconclusive})</button>`;
    html += `<button class="filter-pill" data-filter="skip" ${counts.skip === 0 ? 'disabled' : ''}>行业缺口 (${counts.skip})</button>`;
    html += `<button class="filter-pill" data-filter="pass" ${counts.pass === 0 ? 'disabled' : ''}>通过 (${counts.pass})</button>`;
    html += `<button class="filter-pill" data-filter="not_applicable" ${counts.not_applicable === 0 ? 'disabled' : ''}>不适用 (${counts.not_applicable})</button>`;
    html += '</div>';
    const failItems = sortedResults.filter(r => r.status === 'fail' || r.status === 'error');
    if (failItems.length > 0) {
        html += `<div class="fail-summary">`;
        html += `<div class="fail-summary-header">⚠️ ${failItems.length} 项失败</div>`;
        html += `<div class="table-scroll"><table class="fail-summary-table"><thead><tr><th>ID</th><th>测试项</th><th>说明</th></tr></thead><tbody>`;
        failItems.forEach(r => {
            html += `<tr><td>${r.test_id}</td><td>${TEST_NAME_ZH[r.test_name] || r.test_name}</td><td>${escapeHtml(localizeMessage(r.message))}</td></tr>`;
        });
        html += `</tbody></table></div></div>`;
    }
    // Group by category — card list layout
    html += '<div id="detail-tests-table" class="test-list">';
    const detailCatGroups = {};
    CATEGORY_META.forEach(c => { detailCatGroups[c.key] = []; });
    sortedResults.forEach(r => {
        const cat = TEST_CATEGORY[r.test_name] || 'wallet_core';
        if (detailCatGroups[cat]) detailCatGroups[cat].push(r);
    });
    CATEGORY_META.forEach(c => {
        const groupResults = detailCatGroups[c.key];
        if (groupResults.length === 0) return;
        html += `<div class="test-list-group matrix-group-header" data-cat="${c.key}">${c.label}</div>`;
        for (const r of groupResults) {
            const ownerLabel = r.owner === 'provider'
                ? (r.status === 'fail' ? '供应商问题' : '供应商不支持')
                : r.owner === 'benchmark' ? '基准限制'
                : r.owner === 'industry' ? '行业缺口' : '';
            const ownerBadge = ownerLabel
                ? ` <span class="owner-badge owner-${r.owner}">${ownerLabel}</span>` : '';
            const statusIcon = r.status === 'not_applicable' ? '<span class="status-na">N/A</span>' : (STATUS_ICONS[r.status] || '?');
            const statusText = r.status === 'not_applicable' ? '' : (STATUS_ZH[r.status] || r.status);
            const latency = getLatencyMs(r) > 0 ? ` · ${getLatencyMs(r).toFixed(0)}ms` : '';
            const msg = localizeMessage(r.message);
            html += `<div class="test-list-item" data-status="${r.status}" data-cat="${c.key}">
                <div class="test-list-row1">
                    <span class="test-list-icon ${STATUS_CLASS[r.status] || ''}">${statusIcon}</span>
                    <span class="test-list-name">${TEST_NAME_ZH[r.test_name] || r.test_name}</span>
                    <span class="test-list-meta">${statusText}${latency}</span>
                    ${ownerBadge}
                </div>
                ${msg ? `<div class="test-list-row2">${escapeHtml(msg)}</div>` : ''}
            </div>`;
        }
    });
    html += '</div>';
    html += '</div>'; // #detail-tests

    // ========== Tab 3: 开发体验评估 ==========
    html += '<div class="detail-tab-pane hidden" id="detail-eval">';
    if (provider.evaluation) {
        html += renderEvaluation(provider);
    } else {
        html += '<p class="loading">暂无评估数据</p>';
    }
    html += '</div>'; // #detail-eval

    // ========== Tab 4: Agent 备忘 ==========
    html += '<div class="detail-tab-pane hidden" id="detail-memo">';
    const memoEv = provider.evaluation;
    const hasAgentExp = memoEv?.agent_experience;
    const hasAgentMemo = memoEv?.agent_memo;
    if (hasAgentExp || hasAgentMemo) {
        // Agent 集成体验（从开发体验评估迁移过来）
        if (hasAgentExp) {
            html += `<div class="memo-card" style="margin-bottom:var(--space-l)">`;
            html += `<div class="memo-card-header"><h3>Agent 集成体验概述</h3></div>`;
            html += `<div class="memo-wrapper" style="max-height:none">`;
            html += `<div class="eval-memo">${renderMemo(sanitizeText(memoEv.agent_experience))}</div>`;
            html += `</div>`;
            html += `</div>`;
        }
        // Agent 备忘录原文
        if (hasAgentMemo) {
            const memoId = 'memo-' + Date.now();
            const providerName = provider.provider_meta?.name || provider.provider;
            // CTA banner
            html += `<div class="memo-cta">`;
            html += `<div class="memo-cta-text">`;
            html += `<span class="memo-cta-title">📋 一键复制，粘贴给你的 AI Agent</span>`;
            html += `<span class="memo-cta-desc">下方备忘录包含 ${escapeHtml(providerName)} 的接口规范、踩坑记录和代码示例。复制后直接粘贴到 ChatGPT / Claude / Cursor 等 AI 工具中，即可辅助完成集成开发。</span>`;
            html += `</div>`;
            html += `<button class="memo-cta-btn" onclick="copyMemo(this, '${memoId}')">复制给我的 Agent</button>`;
            html += `</div>`;
            // Memo card
            html += `<div class="memo-card">`;
            html += `<div class="memo-card-header"><h3>Agent 集成备忘录</h3>`;
            html += `<button class="memo-copy-icon" onclick="copyMemo(this, '${memoId}')" title="复制全文"><svg width="16" height="16" viewBox="0 0 16 16" fill="none"><rect x="5" y="5" width="8" height="9" rx="1.5" stroke="currentColor" stroke-width="1.3"/><path d="M3 10V3.5A1.5 1.5 0 014.5 2H9" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/></svg></button></div>`;
            html += `<div class="memo-wrapper" style="max-height:none">`;
            html += `<div class="eval-memo" id="${memoId}" data-raw="${escapeHtml(sanitizeText(memoEv.agent_memo))}">${renderMemo(sanitizeText(memoEv.agent_memo))}</div>`;
            html += `</div>`;
            html += '</div>';
        }
    } else {
        html += '<p class="loading">暂无 Agent 备忘录</p>';
    }
    html += '</div>'; // #detail-memo

    container.innerHTML = html;

    // ---- Post-render: Mini-Radar Chart ----
    const detailRadarCtx = document.getElementById('detail-score-radar')?.getContext('2d');
    if (detailRadarCtx) {
        const scores = computeRadarScores(provider);
        const radarColor = PROVIDER_COLORS[provider.provider] || getCssVar('--text-tertiary');
        const radarLabels = RADAR_DIMENSIONS.map(d => d.label);
        const radarData = RADAR_DIMENSIONS.map(d => scores[d.key]);

        new Chart(detailRadarCtx, {
            type: 'radar',
            data: {
                labels: radarLabels,
                datasets: [{
                    label: provider.provider_meta?.name || provider.provider,
                    data: radarData,
                    borderColor: radarColor,
                    backgroundColor: `${radarColor}33`,
                    pointBackgroundColor: radarColor,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: {
                    r: {
                        angleLines: { color: getCssVar('--bg-border') },
                        grid: { color: getCssVar('--bg-border') },
                        pointLabels: { display: false },
                        ticks: { display: false, backdropColor: 'transparent', stepSize: 25 },
                        suggestedMin: 0,
                        suggestedMax: 100,
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) { label += ': '; }
                                if (context.parsed.r !== null) {
                                    label += context.parsed.r.toFixed(1);
                                }
                                return label;
                            }
                        }
                    }
                },
            }
        });
    }

    // ---- Post-render: Sub-nav tab switching ----
    detailNav.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', (e) => {
            e.preventDefault();
            const targetId = link.getAttribute('href').substring(1);
            detailNav.querySelectorAll('a').forEach(a => a.classList.remove('active'));
            link.classList.add('active');
            container.querySelectorAll('.detail-tab-pane').forEach(p => p.classList.add('hidden'));
            const target = container.querySelector('#' + targetId);
            if (target) target.classList.remove('hidden');
        });
    });
    // Default: activate first tab (clear any stale active state first)
    detailNav.querySelectorAll('a').forEach(a => a.classList.remove('active'));
    detailNav.querySelector('a')?.classList.add('active');

    // ---- Post-render: Filter pills (Tab 2) ----
    container.querySelectorAll('.filter-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.disabled) return;
            container.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const filter = btn.dataset.filter;
            const items = [...container.querySelectorAll('#detail-tests-table > .test-list-item, #detail-tests-table > .test-list-group')];
            // First pass: show/hide data items
            items.forEach(el => {
                if (el.classList.contains('test-list-group')) return;
                if (filter === 'all') { el.style.display = ''; return; }
                const status = el.dataset.status;
                if (filter === 'fail') {
                    el.style.display = (status === 'fail' || status === 'error') ? '' : 'none';
                } else {
                    el.style.display = status === filter ? '' : 'none';
                }
            });
            // Second pass: show group headers only if they have visible children
            items.forEach((el, i) => {
                if (!el.classList.contains('test-list-group')) return;
                if (filter === 'all') { el.style.display = ''; return; }
                let hasVisible = false;
                for (let j = i + 1; j < items.length; j++) {
                    if (items[j].classList.contains('test-list-group')) break;
                    if (items[j].style.display !== 'none') { hasVisible = true; break; }
                }
                el.style.display = hasVisible ? '' : 'none';
            });
        });
    });

    // ---- Post-render: Memo collapse (Tab 4) ----
    const memoWrapper = container.querySelector('.memo-wrapper');
    if (memoWrapper) {
        const memoContent = memoWrapper.querySelector('.eval-memo');
        const gradient = memoWrapper.querySelector('.memo-gradient');
        const toggleBtn = container.querySelector('.memo-toggle-btn');
        const MAX_HEIGHT = 150;
        requestAnimationFrame(() => {
            if (memoContent.scrollHeight <= MAX_HEIGHT) {
                gradient.style.display = 'none';
                toggleBtn.style.display = 'none';
                memoWrapper.style.maxHeight = 'none';
            } else {
                memoWrapper.style.maxHeight = MAX_HEIGHT + 'px';
                memoWrapper.style.overflow = 'hidden';
                memoWrapper.style.position = 'relative';
            }
        });
        if (toggleBtn) toggleBtn.addEventListener('click', () => {
            const isCollapsed = memoWrapper.style.maxHeight !== 'none';
            if (isCollapsed) {
                memoWrapper.style.maxHeight = 'none';
                memoWrapper.style.overflow = 'visible';
                gradient.style.display = 'none';
                toggleBtn.textContent = '收起 ▲';
            } else {
                memoWrapper.style.maxHeight = MAX_HEIGHT + 'px';
                memoWrapper.style.overflow = 'hidden';
                gradient.style.display = '';
                toggleBtn.textContent = '展开全文 ▼';
            }
        });
    }
}
function renderDetailCard(title, value) {
    return `<div class="detail-card"><h3>${title}</h3><div>${value || '—'}</div></div>`;
}

const DX_SCORE_META = {
    onboarding_ease:       { label: "接入便利度",   levels: ["极难", "较难", "中等", "低摩擦", "零摩擦"] },
    doc_quality:           { label: "文档质量",     levels: ["严重误导", "较差", "一般", "良好", "精准"] },
    api_consistency:       { label: "API 一致性",   levels: ["处处意外", "较多意外", "一般", "基本一致", "完全一致"] },
    error_message_quality: { label: "错误信息质量", levels: ["不可读", "较差", "一般", "较好", "清晰可操作"] },
    agent_autonomy:        { label: "Agent 自主度", levels: ["完全依赖人类", "较低", "中等", "高自主", "全自主"] },
};

function dxTagColor(score) {
    if (score >= 4) return 'var(--color-pass)';
    if (score === 3) return 'var(--color-skip)';
    return 'var(--color-fail)';
}

function renderEvaluation(provider) {
    const ev = provider.evaluation;
    if (!ev) return '';
    let html = '<div class="eval-section">';

    // 评估者 & 日期
    html += `<p class="eval-meta">评估者: ${escapeHtml(ev.evaluator || '—')} | 日期: ${ev.date || '—'}</p>`;

    // 总结
    if (ev.summary) {
        const lines = sanitizeText(ev.summary).trim().split(/\n/).map(s => s.trim()).filter(Boolean);
        html += '<ul class="eval-summary-list">';
        lines.forEach(line => { html += `<li>${escapeHtml(line).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</li>`; });
        html += '</ul>';
    }

    // DX 评分标签
    const scores = ev.scores || {};
    const dxKeys = Object.keys(DX_SCORE_META);
    const hasDx = dxKeys.some(k => scores[k] != null);
    if (hasDx) {
        html += '<h4>开发体验</h4><div class="eval-dx-grid">';
        for (const key of dxKeys) {
            const val = scores[key];
            if (val == null) continue;
            const meta = DX_SCORE_META[key];
            const text = meta.levels[val - 1] || `${val}/5`;
            const color = dxTagColor(val);
            html += `<div class="eval-dx-item"><span class="eval-dx-label">${meta.label}</span><span class="tag" style="background:${color};color:#fff;border-color:${color}">${text}</span></div>`;
        }
        if (scores.time_to_first_success_min != null) {
            html += `<div class="eval-dx-item"><span class="eval-dx-label">首次成功耗时</span><span class="eval-dx-value">${scores.time_to_first_success_min} 分钟</span></div>`;
        }
        html += '</div>';
    }

    // ISSUE-008: 维度评分 (e01-e06 + t27)
    const EVAL_SCORE_META = {
        governance_completeness: { label: '治理完整度', levels: ['无治理', '基础限额/白名单', '限额+白名单+时间窗', '+多签/审批流', '完整策略引擎'] },
        network_environment:     { label: '环境矩阵',   levels: ['仅主网', 'testnet 需人工 faucet', 'testnet+auto faucet', '完整 testnet/mainnet', '+本地 devnet'] },
        sdk_doc_quality:         { label: '文档上手度', levels: ['无文档', '严重过时', '需试错', '准确+可运行示例', '完美+quickstart+llms.txt'] },
        app_tool_coverage:       { label: '工具覆盖度', levels: ['无工具', '1-5 工具', '6-15 工具', '16-30 工具', '30+ 全覆盖'] },
        app_execution_quality:   { label: '执行质量',   levels: ['常失败', '高滑点/延迟', '可靠无优化', '低滑点+高成功率', '最优路由+MEV保护'] },
        cost_transparency:       { label: '定价透明度', levels: ['无定价信息', '限制不明确', '基础定价页', '清晰定价+免费额度', '完全透明+仪表盘'] },
        kyc_requirement_clarity: { label: 'KYC 清晰度', levels: ['未知要求', '需 KYC 但不清楚', 'KYC 文档+复杂', '明确+简单流程', '无 KYC 或全自动'] },
    };
    const evalKeys = Object.keys(EVAL_SCORE_META);
    const hasEval = evalKeys.some(k => scores[k] != null);
    if (hasEval) {
        html += '<h4>维度评分</h4><div class="eval-dx-grid">';
        for (const key of evalKeys) {
            const val = scores[key];
            if (val == null) continue;
            const meta = EVAL_SCORE_META[key];
            const text = meta.levels[val - 1] || `${val}/5`;
            const color = dxTagColor(val);
            html += `<div class="eval-dx-item eval-yaml-source"><span class="eval-dx-label">${meta.label} <span class="data-source-badge badge-yaml">人工</span></span><span class="tag" style="background:${color};color:#fff;border-color:${color}">${text}</span></div>`;
        }
        html += '</div>';
    }

    // 需人工介入的操作
    const interventions = ev.human_interventions || [];
    if (interventions.length > 0) {
        html += '<h4>需人工介入的操作</h4><ul class="eval-list">';
        interventions.forEach(h => {
            const blockerTag = h.blocker ? '<span class="tag" style="background:var(--color-fail);color:#fff;border-color:var(--color-fail)">blocker</span> ' : '';
            html += `<li>${blockerTag}<strong>${escapeHtml(h.type)}</strong> — ${escapeHtml(sanitizeText(h.reason))}</li>`;
        });
        html += '</ul>';
    }

    // 集成 Bug
    const bugs = ev.integration_bugs || [];
    if (bugs.length > 0) {
        html += '<h4>集成 Bug</h4><div class="table-scroll"><table class="data-table"><thead><tr><th>ID</th><th>描述</th><th>根因</th><th>修复耗时</th></tr></thead><tbody>';
        bugs.forEach(b => {
            html += `<tr><td>${escapeHtml(b.id)}</td><td>${escapeHtml(sanitizeText(b.description))}</td><td>${escapeHtml(b.root_cause)}</td><td>${b.fix_time_min} 分钟</td></tr>`;
        });
        html += '</tbody></table></div>';
    }

    // 文档缺陷
    const gaps = ev.doc_gaps || [];
    if (gaps.length > 0) {
        html += '<h4>文档缺陷</h4><ul class="eval-list">';
        gaps.forEach(g => html += `<li>${escapeHtml(sanitizeText(g))}</li>`);
        html += '</ul>';
    }

    html += '</div>';
    return html;
}

function renderMemo(memo) {
    const lines = memo.split('\n');
    const out = [];
    let inCode = false, codeLines = [];
    let listStack = []; // 'ul' or 'ol'
    let tableRows = [];

    function inline(text) {
        return escapeHtml(text)
            .replace(/`([^`]+)`/g, '<code class="memo-code">$1</code>')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    }

    function flushList() {
        while (listStack.length) out.push(`</${listStack.pop()}>`);
    }

    function flushTable() {
        if (!tableRows.length) return;
        let t = '<div class="table-scroll"><table class="data-table">';
        tableRows.forEach((cells, i) => {
            const tag = i === 0 ? 'th' : 'td';
            if (i === 1 && cells.every(c => /^[-:]+$/.test(c.trim()))) return; // separator row
            t += '<tr>' + cells.map(c => `<${tag}>${inline(c.trim())}</${tag}>`).join('') + '</tr>';
        });
        t += '</table></div>';
        out.push(t);
        tableRows = [];
    }

    for (const raw of lines) {
        const line = raw;

        // Code block toggle
        if (line.trimStart().startsWith('```')) {
            if (inCode) {
                out.push('<pre class="memo-pre">' + escapeHtml(codeLines.join('\n')) + '</pre>');
                codeLines = [];
            }
            inCode = !inCode;
            continue;
        }
        if (inCode) { codeLines.push(line); continue; }

        // Table row
        if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
            flushList();
            const cells = line.trim().slice(1, -1).split('|');
            tableRows.push(cells);
            continue;
        } else {
            flushTable();
        }

        // Headings
        const h3m = line.match(/^###\s+(.*)/);
        if (h3m) { flushList(); out.push(`<h4 class="memo-h4">${inline(h3m[1])}</h4>`); continue; }
        const h2m = line.match(/^##\s+(.*)/);
        if (h2m) { flushList(); out.push(`<h3 class="memo-h3">${inline(h2m[1])}</h3>`); continue; }
        const h1m = line.match(/^#\s+(.*)/);
        if (h1m) { flushList(); out.push(`<h2 class="memo-h2">${inline(h1m[1])}</h2>`); continue; }

        // Unordered list
        const ulm = line.match(/^\s*[-*]\s+(.*)/);
        if (ulm) {
            if (!listStack.length || listStack[listStack.length - 1] !== 'ul') {
                flushList();
                out.push('<ul>');
                listStack.push('ul');
            }
            out.push(`<li>${inline(ulm[1])}</li>`);
            continue;
        }

        // Ordered list
        const olm = line.match(/^\s*\d+\.\s+(.*)/);
        if (olm) {
            if (!listStack.length || listStack[listStack.length - 1] !== 'ol') {
                flushList();
                out.push('<ol>');
                listStack.push('ol');
            }
            out.push(`<li>${inline(olm[1])}</li>`);
            continue;
        }

        // Close list if not continuing
        flushList();

        // Empty line or text
        const trimmed = line.trim();
        if (!trimmed) { out.push(''); continue; }
        out.push(`<p>${inline(trimmed)}</p>`);
    }

    flushList();
    flushTable();
    if (inCode && codeLines.length) {
        out.push('<pre class="memo-pre">' + escapeHtml(codeLines.join('\n')) + '</pre>');
    }

    return out.join('\n');
}

function copyMemo(btn, id) {
    const memoEl = document.getElementById(id);
    if (!memoEl) return;
    const rawMemo = memoEl.dataset.raw;
    const original = btn.innerHTML;
    const isCta = btn.classList.contains('memo-cta-btn');
    navigator.clipboard.writeText(rawMemo).then(() => {
        if (isCta) {
            btn.textContent = '✅ 已复制';
        } else {
            btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M3 8.5L6.5 12L13 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>';
        }
        btn.classList.add('copied');
        setTimeout(() => {
            if (isCta) btn.textContent = '复制给我的 Agent';
            else btn.innerHTML = original;
            btn.classList.remove('copied');
        }, 2000);
    });
}


// --------------------------------------------------------------------------
// Tab: 钱包集成类型
// --------------------------------------------------------------------------
function renderWalletTypesTab() {
    const container = document.getElementById('wallet-types-container');
    if (!container || container.dataset.rendered) return;
    container.dataset.rendered = '1';

    container.innerHTML = `
    <div class="wt-article">
      <h1>AI Agent 钱包集成方式对比</h1>
      <p class="wt-meta"><strong>日期</strong>: 2026-03-05 &nbsp;|&nbsp; <strong>适用</strong>: wallet-bench 所有 provider</p>

      <nav class="wt-toc">
        <h4 class="wt-toc-title">目录</h4>
        <ol class="wt-toc-list">
          <li><a href="#wt-why">为什么集成方式很重要？</a></li>
          <li><a href="#wt-six">六种集成方式一览</a></li>
          <li><a href="#wt-mcp">MCP Server（最优）</a></li>
          <li><a href="#wt-plugin">OpenClaw Plugin</a></li>
          <li><a href="#wt-sdk">Python / TypeScript SDK</a></li>
          <li><a href="#wt-cli">CLI Subprocess</a></li>
          <li><a href="#wt-skill">SKILL.md（Prompt 注入）</a></li>
          <li><a href="#wt-rest">REST API（最原始）</a></li>
          <li><a href="#wt-compare">综合对比</a></li>
          <li><a href="#wt-providers">各 Provider 的集成方式</a></li>
          <li><a href="#wt-trends">趋势观察</a></li>
        </ol>
      </nav>

      <h2 id="wt-why">为什么集成方式很重要？</h2>
      <p>对 AI Agent 而言，钱包的<strong>集成方式</strong>决定了：</p>
      <ul>
        <li><strong>接入成本</strong> — 需要写多少代码才能让 Agent 调用钱包？</li>
        <li><strong>可靠性</strong> — Agent 调用是否有类型安全、schema 校验？</li>
        <li><strong>可移植性</strong> — 能否跨 Agent 框架（Claude、LangChain、AutoGen）复用？</li>
        <li><strong>发现性</strong> — Agent 能否自动发现钱包的能力（tool list），还是需要人写 prompt？</li>
      </ul>
      <p>选错集成方式，可能意味着 <strong>3 天的适配工作</strong> vs <strong>3 分钟的 npx 启动</strong>。</p>

      <h2 id="wt-six">六种集成方式一览</h2>
      <table class="data-table">
        <thead><tr><th style="text-align:center">排序</th><th>集成方式</th><th style="text-align:center">Agent 友好度</th><th>代表 Provider</th></tr></thead>
        <tbody>
          <tr><td style="text-align:center">1</td><td><strong>MCP Server</strong></td><td style="text-align:center">⭐⭐⭐⭐⭐</td><td>Privy, BNB Chain MCP, Crossmint</td></tr>
          <tr><td style="text-align:center">2</td><td><strong>OpenClaw Plugin</strong></td><td style="text-align:center">⭐⭐⭐⭐</td><td>Crossmint (lobster.cash)</td></tr>
          <tr><td style="text-align:center">3</td><td><strong>Python/TS SDK</strong></td><td style="text-align:center">⭐⭐⭐½</td><td>Coinbase AgentKit</td></tr>
          <tr><td style="text-align:center">4</td><td><strong>CLI Subprocess</strong></td><td style="text-align:center">⭐⭐⭐</td><td>MoonPay, Minara</td></tr>
          <tr><td style="text-align:center">5</td><td><strong>SKILL.md (Prompt 注入)</strong></td><td style="text-align:center">⭐⭐½</td><td>Privy (OpenClaw Skill)</td></tr>
          <tr><td style="text-align:center">6</td><td><strong>REST API</strong></td><td style="text-align:center">⭐⭐</td><td>(各家的底层 API)</td></tr>
        </tbody>
      </table>

      <h2 id="wt-mcp">1. MCP Server（最优）</h2>
      <pre class="memo-pre"><code>Agent &lt;-stdio-&gt; MCP Server &lt;-HTTP-&gt; Provider API</code></pre>
      <p><strong>Model Context Protocol (MCP)</strong> 是 Anthropic 于 2024 年提出的开放协议，定义了 AI Agent 与外部工具之间的标准通信方式。</p>
      <h3>为什么最好</h3>
      <table class="data-table">
        <thead><tr><th>优势</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td><strong>协议标准化</strong></td><td>tool name、参数 schema（Zod/JSON Schema）、返回格式全部 typed，Agent 不需要"猜"怎么调用</td></tr>
          <tr><td><strong>零代码集成</strong></td><td><code class="memo-code">npx @privy-io/mcp-server</code> 或 <code class="memo-code">npx @bnb-chain/mcp</code> 即用</td></tr>
          <tr><td><strong>双向通信</strong></td><td>Server 可主动推送 progress、log，不只是 request-response</td></tr>
          <tr><td><strong>跨框架复用</strong></td><td>Claude Desktop、Cursor、Claude Code、LangChain、AutoGen 都原生支持</td></tr>
          <tr><td><strong>自动发现</strong></td><td>Agent 调用 <code class="memo-code">list_tools()</code> 即可获取所有可用工具和参数定义</td></tr>
        </tbody>
      </table>
      <h3>局限</h3>
      <ul>
        <li>进程常驻（stdio transport），多 provider 并行时占资源</li>
        <li>如果 MCP Server 非官方出品，质量可能参差不齐</li>
        <li>仍需 API 凭证（App ID / Secret / Private Key）</li>
      </ul>
      <h3>实际示例</h3>
      <p><strong>Privy MCP Server</strong> — 25+ typed tools：</p>
      <pre class="memo-pre"><code>{
  "mcpServers": {
    "privy": {
      "command": "npx",
      "args": ["@privy-io/mcp-server"],
      "env": {
        "PRIVY_APP_ID": "your-app-id",
        "PRIVY_APP_SECRET": "your-app-secret"
      }
    }
  }
}</code></pre>
      <p>Agent 自动获得 <code class="memo-code">create_wallet</code>、<code class="memo-code">personal_sign</code>、<code class="memo-code">eth_sendTransaction</code>、<code class="memo-code">create_policy</code> 等工具，无需手写任何 adapter。</p>
      <p><strong>BNB Chain MCP</strong> — BSC/opBNB 链上操作：</p>
      <pre class="memo-pre"><code>{
  "mcpServers": {
    "bnbchain": {
      "command": "npx",
      "args": ["-y", "@bnb-chain/mcp"],
      "env": {
        "PRIVATE_KEY": "0x..."
      }
    }
  }
}</code></pre>

      <h2 id="wt-plugin">2. OpenClaw Plugin</h2>
      <pre class="memo-pre"><code>Agent (OpenClaw daemon) &lt;-in-process-&gt; Plugin Runtime &lt;-HTTP-&gt; Provider API</code></pre>
      <p>OpenClaw 是 2026 年最流行的开源 AI Agent 框架（264k+ GitHub Stars），其插件系统允许 npm 包直接注入 Agent 运行时。</p>
      <h3>特点</h3>
      <table class="data-table">
        <thead><tr><th>优势</th><th>局限</th></tr></thead>
        <tbody>
          <tr><td>类 MCP 的 typed 体验</td><td><strong>锁死在 OpenClaw 生态</strong></td></tr>
          <tr><td>npm install 即用</td><td>不兼容 Claude Desktop / LangChain</td></tr>
          <tr><td>进程内执行，低延迟</td><td>插件安全性依赖 OpenClaw 审核</td></tr>
          <tr><td>可共享本地密钥存储</td><td>生态较新，插件数量有限</td></tr>
        </tbody>
      </table>
      <h3>实际示例</h3>
      <p><strong>lobster.cash</strong> — Crossmint 的 OpenClaw 支付插件：</p>
      <pre class="memo-pre"><code>openclaw plugins install @crossmint/lobster.cash</code></pre>
      <p>独特之处：</p>
      <ul>
        <li>本地 ed25519 密钥 + 委托签名（Agent 密钥不出机）</li>
        <li><strong>Visa 虚拟信用卡</strong>（Agent 可以在法币世界消费）</li>
        <li><strong>x402 支付协议</strong>（HTTP 402 自动付款）</li>
        <li>Solana USDC 链上支付</li>
      </ul>
      <p>这意味着 Agent 不仅能做链上交易，还能<strong>刷信用卡购物</strong> — 这是纯 REST API 集成无法覆盖的能力维度。</p>

      <h2 id="wt-sdk">3. Python / TypeScript SDK</h2>
      <pre class="memo-pre"><code>Agent &lt;-function call-&gt; SDK (typed) &lt;-HTTP-&gt; Provider API</code></pre>
      <h3>特点</h3>
      <table class="data-table">
        <thead><tr><th>优势</th><th>局限</th></tr></thead>
        <tbody>
          <tr><td>完整类型安全（Pydantic / TypeScript）</td><td>需要写代码，管理依赖</td></tr>
          <tr><td>同步调用，错误处理清晰</td><td>绑定特定语言</td></tr>
          <tr><td>IDE 补全、调试友好</td><td>无自动 tool 发现（需人写 wrapper）</td></tr>
        </tbody>
      </table>
      <h3>实际示例</h3>
      <p><strong>Coinbase AgentKit</strong> — Python SDK：</p>
      <pre class="memo-pre"><code>from coinbase_agentkit import AgentKit, CdpEvmWalletProvider

wallet = CdpEvmWalletProvider(network_id="base-sepolia")
kit = AgentKit(wallet_provider=wallet)

# 类型安全的函数调用
result = kit.run_action("transfer", {
    "amount": "0.001",
    "asset_id": "eth",
    "destination": "0x..."
})</code></pre>
      <p>SDK 的优势在于 <strong>类型安全和 IDE 体验</strong>，但相比 MCP，Agent 无法自动发现可用工具 — 需要人类开发者写 LangChain Tool wrapper。</p>

      <h2 id="wt-cli">4. CLI Subprocess</h2>
      <pre class="memo-pre"><code>Agent → subprocess.Popen → \`cli-tool --arg1 val1 --json\` → parse stdout</code></pre>
      <h3>特点</h3>
      <table class="data-table">
        <thead><tr><th>优势</th><th>局限</th></tr></thead>
        <tbody>
          <tr><td>安装简单（npm install -g）</td><td>每次调用 fork 新进程，冷启动开销大</td></tr>
          <tr><td>一条命令一个动作，语义清晰</td><td>输出格式不保证（\`--json\` 可能不输出 JSON）</td></tr>
          <tr><td>不需要理解 HTTP 认证</td><td>交互式 prompt 会阻塞自动化</td></tr>
          <tr><td>非托管方案，密钥本地</td><td>错误处理靠 exit code + stderr 文本解析</td></tr>
        </tbody>
      </table>
      <h3>实际示例</h3>
      <p><strong>MoonPay CLI</strong>：</p>
      <pre class="memo-pre"><code>mp wallet create --json
# {"address": "0x...", "type": "evm", "chain": "ethereum"}

mp send --to 0x... --amount 0.01 --chain ethereum --json</code></pre>
      <p>MoonPay 的 <code class="memo-code">--json</code> 输出较可靠。但 <strong>Minara 的 <code class="memo-code">--json</code> flag 实际不输出 JSON</strong> — 这是 CLI 集成的最大风险：你无法信任 flag 文档，必须实际验证。</p>
      <h3>CLI 的特殊问题</h3>
      <ol>
        <li><strong>交互式 UI 阻塞</strong>：Minara 的 token 选择器弹出 inquirer UI，必须用 <code class="memo-code">stdin=DEVNULL</code> 防止卡死</li>
        <li><strong>进程管理</strong>：subprocess 需要超时控制、僵尸进程清理</li>
        <li><strong>输出解析脆弱</strong>：CLI 输出可能包含 ANSI 颜色码、进度条等干扰字符</li>
      </ol>

      <h2 id="wt-skill">5. SKILL.md（Prompt 注入）</h2>
      <pre class="memo-pre"><code>Agent &lt;- system prompt injection -&gt; SKILL.md (markdown) → Agent 自行调用 REST API</code></pre>
      <h3>特点</h3>
      <table class="data-table">
        <thead><tr><th>优势</th><th>局限</th></tr></thead>
        <tbody>
          <tr><td><strong>最轻量</strong> — 纯文本文件</td><td><strong>最不可靠</strong> — 完全靠 LLM 理解力</td></tr>
          <tr><td>无运行时依赖</td><td>无类型安全，无 schema 校验</td></tr>
          <tr><td>跨 LLM 通用（Claude/GPT/Cursor）</td><td>复杂操作容易"幻觉"（编造参数）</td></tr>
          <tr><td>安装到 <code class="memo-code">~/.openclaw/skills/</code></td><td>安全指令可被 prompt injection 绕过</td></tr>
        </tbody>
      </table>
      <h3>工作原理</h3>
      <p>SKILL.md 被注入到 Agent 的 system prompt 中，告诉 Agent "你有以下 REST API 可用"。Agent 读完说明后，<strong>自行构造 HTTP 请求</strong>。</p>
      <pre class="memo-pre"><code>## 创建钱包
POST /api/v1/wallets
Headers: Authorization: Basic {base64(APP_ID:APP_SECRET)}
Body: {"chain_type": "ethereum"}
Response: {"id": "wallet_xxx", "address": "0x..."}</code></pre>
      <p>这本质上是<strong>让 LLM 当 HTTP 客户端</strong> — 能力上限取决于 LLM 对 REST API 的理解。适合简单场景，不适合需要精确参数的链上操作。</p>

      <h2 id="wt-rest">6. REST API（最原始）</h2>
      <pre class="memo-pre"><code>Agent → 自定义 adapter 代码 → HTTP client → Provider REST API</code></pre>
      <h3>特点</h3>
      <table class="data-table">
        <thead><tr><th>优势</th><th>局限</th></tr></thead>
        <tbody>
          <tr><td>最灵活，任何语言/框架可用</td><td>接入成本最高</td></tr>
          <tr><td>完全控制请求/响应</td><td>需自行处理认证、序列化、重试</td></tr>
          <tr><td>无中间层开销</td><td>Agent 无法自动发现能力</td></tr>
          <tr><td>适合定制化需求</td><td>每个 provider 的 API 风格不同</td></tr>
        </tbody>
      </table>
      <p>REST API 是所有其他方式的<strong>底层基础</strong> — MCP Server、SDK、CLI 最终都是在调用 REST API。直接用 REST API 给了最大灵活性，但代价是最高的集成成本。</p>

      <h2 id="wt-compare">综合对比</h2>
      <h3>定量评估</h3>
      <div style="overflow-x:auto">
        <table class="data-table">
          <thead><tr><th>维度</th><th style="text-align:center">MCP</th><th style="text-align:center">Plugin</th><th style="text-align:center">SDK</th><th style="text-align:center">CLI</th><th style="text-align:center">SKILL.md</th><th style="text-align:center">REST</th></tr></thead>
          <tbody>
            <tr><td>接入代码量</td><td style="text-align:center"><strong>0 行</strong></td><td style="text-align:center"><strong>0 行</strong></td><td style="text-align:center">~50 行</td><td style="text-align:center">~30 行</td><td style="text-align:center"><strong>0 行</strong></td><td style="text-align:center">~200 行</td></tr>
            <tr><td>类型安全</td><td style="text-align:center">✅ Zod</td><td style="text-align:center">✅ TS</td><td style="text-align:center">✅</td><td style="text-align:center">❌</td><td style="text-align:center">❌</td><td style="text-align:center">❌</td></tr>
            <tr><td>自动 tool 发现</td><td style="text-align:center">✅ <code class="memo-code">list_tools</code></td><td style="text-align:center">✅</td><td style="text-align:center">❌</td><td style="text-align:center">❌</td><td style="text-align:center">❌</td><td style="text-align:center">❌</td></tr>
            <tr><td>跨框架复用</td><td style="text-align:center">✅</td><td style="text-align:center">❌ OpenClaw only</td><td style="text-align:center">❌ 语言绑定</td><td style="text-align:center">✅</td><td style="text-align:center">✅</td><td style="text-align:center">✅</td></tr>
            <tr><td>调用延迟</td><td style="text-align:center">~同 REST</td><td style="text-align:center">进程内更低</td><td style="text-align:center">~同 REST</td><td style="text-align:center">+200ms 进程开销</td><td style="text-align:center">~同 REST</td><td style="text-align:center">基准</td></tr>
            <tr><td>出错可追溯性</td><td style="text-align:center">✅ structured</td><td style="text-align:center">✅</td><td style="text-align:center">✅</td><td style="text-align:center">⚠️ stderr</td><td style="text-align:center">❌</td><td style="text-align:center">⚠️ HTTP code</td></tr>
            <tr><td>Agent 自主度</td><td style="text-align:center">⭐⭐⭐⭐⭐</td><td style="text-align:center">⭐⭐⭐⭐</td><td style="text-align:center">⭐⭐⭐</td><td style="text-align:center">⭐⭐⭐</td><td style="text-align:center">⭐⭐</td><td style="text-align:center">⭐⭐</td></tr>
          </tbody>
        </table>
      </div>
      <h3>决策树</h3>
      <pre class="memo-pre"><code>你的 Agent 运行在什么框架上？
├─ OpenClaw → 优先用 Plugin，没有则用 MCP
├─ Claude Desktop / Cursor → 用 MCP
├─ LangChain / AutoGen → 用 MCP 或 SDK
├─ 自建框架 (Python) → 用 SDK，没有则 REST
└─ 自建框架 (其他) → 用 CLI，没有则 REST</code></pre>

      <h2 id="wt-providers">wallet-bench 中各 Provider 的集成方式</h2>
      <div style="overflow-x:auto">
      <table class="data-table">
        <thead><tr><th>Provider</th><th>主要集成方式</th><th>替代路径</th><th>独特能力</th></tr></thead>
        <tbody>
          <tr><td><strong>Privy Agentic Wallets</strong></td><td><code class="memo-code">mcp_server_stdio</code></td><td>REST API, OpenClaw Skill</td><td>策略引擎 + 多签 Quorum</td></tr>
          <tr><td><strong>BNB Chain MCP</strong></td><td><code class="memo-code">mcp_server_stdio</code></td><td>—</td><td>零注册，毫秒级</td></tr>
          <tr><td><strong>Crossmint Wallets</strong></td><td><code class="memo-code">mcp_server_stdio</code></td><td>OpenClaw Plugin, REST</td><td>Visa 虚拟卡 + x402</td></tr>
          <tr><td><strong>MoonPay Agents</strong></td><td><code class="memo-code">cli_subprocess</code></td><td><code class="memo-code">mp mcp</code> 转 MCP</td><td>54 工具, 10 链</td></tr>
          <tr><td><strong>Coinbase AgentKit</strong></td><td><code class="memo-code">python_sdk</code></td><td>—</td><td>内置 faucet</td></tr>
          <tr><td><strong>Minara AI</strong></td><td><code class="memo-code">cli_subprocess</code></td><td>—</td><td>DeFi 一站式</td></tr>
        </tbody>
      </table>
      </div>

      <h2 id="wt-trends">趋势观察</h2>
      <h3>2025 → 2026 的变化</h3>
      <pre class="memo-pre"><code>2025: Provider → REST API → 你的代码调用
2026: Provider → MCP Server / Skill → AI Agent 平台自动发现和调用</code></pre>
      <ul>
        <li><strong>Privy</strong> 从纯 REST API 演化为 MCP Server + OpenClaw Skill</li>
        <li><strong>Crossmint</strong> 从纯 REST API 演化为 MCP Server + OpenClaw Plugin (lobster.cash)</li>
        <li><strong>MoonPay</strong> 的 CLI 可通过 <code class="memo-code">mp mcp</code> 一键转为 MCP Server</li>
        <li><strong>MCP 协议</strong>正在成为 AI Agent 工具集成的事实标准</li>
      </ul>
      <h3>对开发者的建议</h3>
      <ol>
        <li><strong>新项目首选 MCP</strong> — 如果 provider 有官方 MCP Server，不要再手写 REST adapter</li>
        <li><strong>评估 provider 时看 <code class="memo-code">integration_type</code></strong> — 这直接决定 Agent 的接入成本</li>
        <li><strong>CLI 谨慎信任</strong> — <code class="memo-code">--json</code> flag 不等于真的输出 JSON，实际验证不可省略</li>
        <li><strong>SKILL.md 适合探索，不适合生产</strong> — 它本质是让 LLM 读说明书自己调 API</li>
      </ol>
      <p class="wt-footer"><em>本文是 wallet-bench 项目的一部分。每个 provider 详情页的「Agent 评估」section 中的集成方式标签均可跳转至本文。</em></p>
    </div>`;
}

// --------------------------------------------------------------------------
// Tab 4: 市场活跃度
// --------------------------------------------------------------------------

const MARKET_PROVIDER_ORDER = ['privy', 'coinbase', 'crossmint', 'bnbchain_mcp', 'moonpay', 'minara', 'okx_onchainos'];
const MARKET_PROVIDER_NAMES = {
    bnbchain_mcp: 'BNB Chain MCP',
    coinbase: 'Coinbase AgentKit',
    crossmint: 'Crossmint',
    privy: 'Privy',
    moonpay: 'MoonPay',
    minara: 'Minara',
    okx_onchainos: 'OKX OnchainOS',
};

let marketDataLoaded = false;

async function loadAndRenderMarketTab() {
    if (marketDataLoaded) return;
    const container = document.getElementById('market-container');
    if (!container) return;
    container.innerHTML = '<p class="loading">加载中...</p>';

    const files = [
        'data/market_npm.json',
        'data/market_pypi.json',
        'data/market_github.json',
        'data/market_status.json',
        'data/market_docs.json',
        'data/market_onchain.json',
    ];
    const results = await Promise.allSettled(files.map(f => fetch(f).then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
    })));

    const [npm, pypi, github, status, docs, onchain] = results.map(r => r.status === 'fulfilled' ? r.value : null);
    renderMarketTab(npm, pypi, github, status, docs, onchain);
    marketDataLoaded = true;
}

function renderMarketTab(npm, pypi, github, status, docs, onchain) {
    const container = document.getElementById('market-container');
    if (!container) return;

    let html = '';

    // Global disclaimer
    html += `<div class="market-disclaimer">⚠️ 本 Tab 展示的是活跃度代理指标，不等于供应商真实 DAU/MAU。所有数据仅用于趋势观察与横向相对比较。</div>`;

    // Card 5 — 可观测用户激活（链上数据）— 置顶
    html += renderMarketCard5(onchain);

    // Card 1 — 开发者兴趣
    html += renderMarketCard1(npm, pypi);

    // Card 2 — 研发健康
    html += renderMarketCard2(github);

    // Card 3 — 服务可靠性
    html += renderMarketCard3(status);

    // Card 4 — 产品成熟度
    html += renderMarketCard4(docs);

    // Data freshness
    html += renderMarketFreshness(npm, pypi, github, status, docs, onchain);

    container.innerHTML = html;
    // Initialize charts after DOM insertion
    initOnchainDailyChart(onchain);
    initChainPieCharts(onchain);
}

function formatNum(n) {
    if (n == null) return '—';
    return n.toLocaleString('en-US');
}

function formatMttr(minutes) {
    if (minutes == null) return '—';
    if (minutes === 0) return '< 1m';
    if (minutes < 60) return `${Math.round(minutes)}m`;
    return `${(minutes / 60).toFixed(1)}h`;
}

function renderMarketCard1(npm, pypi) {
    const downloads = {};
    MARKET_PROVIDER_ORDER.forEach(id => { downloads[id] = 0; });

    if (npm && npm.providers) {
        for (const [id, d] of Object.entries(npm.providers)) {
            if (downloads[id] !== undefined) downloads[id] += (d.total_weekly_downloads || 0);
        }
    }
    if (pypi && pypi.providers) {
        for (const [id, d] of Object.entries(pypi.providers)) {
            if (downloads[id] !== undefined) downloads[id] += (d.total_weekly_downloads || 0);
        }
    }

    // 对数刻度（log10），避免数据悬殊时低值 bar 不可见
    const logMax = Math.log10(Math.max(...Object.values(downloads), 10));
    const rawMax = Math.max(...Object.values(downloads));

    let rows = '';
    MARKET_PROVIDER_ORDER.forEach(id => {
        const val = downloads[id];
        const logVal = val > 0 ? Math.log10(val) : 0;
        const pct = (logVal / logMax * 100).toFixed(1);
        const isMax = val === rawMax;
        rows += `
        <div class="market-bar-row">
            <span class="market-bar-label">${MARKET_PROVIDER_NAMES[id]}</span>
            <div class="market-bar-track">
                <div class="market-bar-fill${isMax ? ' market-bar-max' : ''}" style="width:${pct}%"></div>
            </div>
            <span class="market-bar-value${isMax ? ' market-bar-max-text' : ''}">${formatNum(val)}</span>
        </div>`;
    });

    return `
    <div class="market-card">
        <h3 class="market-card-title">开发者兴趣（npm + PyPI 周下载量）</h3>
        <div class="market-bar-chart">${rows}</div>
        <p class="market-log-note">图表使用对数坐标，右侧数字为实际值</p>
        <div class="market-confidence status-skip">置信度：中 — 含 CI 重复下载，仅看趋势</div>
    </div>`;
}

function renderMarketCard2(github) {
    let rows = '';
    MARKET_PROVIDER_ORDER.forEach(id => {
        const d = github && github.providers && github.providers[id];
        if (!d || (d.total_stars == null && d.repos && d.repos.length === 0)) {
            rows += `<tr>
                <td>${MARKET_PROVIDER_NAMES[id]}</td>
                <td colspan="3" class="market-na">暂无公开仓库</td>
            </tr>`;
        } else {
            rows += `<tr>
                <td>${MARKET_PROVIDER_NAMES[id]}</td>
                <td>${formatNum(d.total_stars)}</td>
                <td>${formatNum(d.total_commits_30d)}</td>
                <td>${formatNum(d.total_open_issues_created_30d)}</td>
            </tr>`;
        }
    });

    return `
    <div class="market-card">
        <h3 class="market-card-title">研发健康（GitHub）</h3>
        <table class="market-table">
            <thead><tr><th>供应商</th><th>Stars</th><th>近 30d Commits</th><th>近 30d Open Issues</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
    </div>`;
}

function renderMarketCard3(status) {
    const noStatusPage = ['bnbchain_mcp', 'moonpay', 'minara', 'okx_onchainos'];
    let rows = '';
    MARKET_PROVIDER_ORDER.forEach(id => {
        const d = status && status.providers && status.providers[id];
        if (!d || (d.status_page_url == null && noStatusPage.includes(id))) {
            rows += `<tr>
                <td>${MARKET_PROVIDER_NAMES[id]}</td>
                <td colspan="2" class="market-na">无公开 Status Page</td>
            </tr>`;
        } else if (d.error) {
            rows += `<tr>
                <td>${MARKET_PROVIDER_NAMES[id]}</td>
                <td colspan="2" class="market-na market-fail-text">数据获取失败</td>
            </tr>`;
        } else {
            const incidents = d.incidents_30d;
            const mttrDisplay = formatMttr(d.mttr_minutes);
            let incidentClass = '';
            if (incidents === 0) incidentClass = ' market-green';
            else if (incidents > 10) incidentClass = ' market-red';
            rows += `<tr>
                <td>${MARKET_PROVIDER_NAMES[id]}</td>
                <td class="${incidentClass}">${incidents != null ? incidents : '—'}</td>
                <td>${mttrDisplay}</td>
            </tr>`;
        }
    });

    return `
    <div class="market-card">
        <h3 class="market-card-title">服务可靠性（Status Page）</h3>
        <table class="market-table">
            <thead><tr><th>供应商</th><th>30d Incidents</th><th>MTTR</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
        <div class="market-confidence status-pass">置信度：高（仅覆盖有公开 Status Page 的供应商）</div>
    </div>`;
}

function renderMarketCard4(docs) {
    let rows = '';
    MARKET_PROVIDER_ORDER.forEach(id => {
        const d = docs && docs.providers && docs.providers[id];
        if (!d || d.total_doc_commits_30d == null) {
            rows += `<tr>
                <td>${MARKET_PROVIDER_NAMES[id]}</td>
                <td class="market-na">—</td>
                <td class="market-na">—</td>
            </tr>`;
        } else {
            const ratio = d.breaking_change_ratio || 0;
            const ratioText = (ratio * 100).toFixed(1) + '%';
            const breakingIcon = ratio > 0 ? ' <span class="market-warn-icon">⚠️</span>' : '';
            rows += `<tr>
                <td>${MARKET_PROVIDER_NAMES[id]}</td>
                <td>${d.total_doc_commits_30d}</td>
                <td>${ratioText}${breakingIcon}</td>
            </tr>`;
        }
    });

    return `
    <div class="market-card">
        <h3 class="market-card-title">产品成熟度（文档变更密度）</h3>
        <table class="market-table">
            <thead><tr><th>供应商</th><th>近 30d 文档 Commits</th><th>Breaking Change 比例</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
        <div class="market-confidence status-skip">置信度：中 — 仅追踪 changelog/docs 目录</div>
    </div>`;
}

function renderMarketCard5(onchain) {
    const PROVIDER_ORDER = ['privy', 'coinbase', 'crossmint', 'bnbchain_mcp', 'moonpay', 'minara', 'okx_onchainos'];

    if (!onchain || !onchain.providers) {
        return `
        <div class="market-card market-card-placeholder">
            <h3 class="market-card-title">可观测用户激活（链上代理）</h3>
            <p class="market-placeholder-text">链上数据采集中，请稍候...</p>
        </div>`;
    }

    // Stale 警告
    let staleWarning = '';
    if (onchain.stale) {
        const staleSince = onchain.stale_since ? new Date(onchain.stale_since).toISOString().slice(0, 10) : '未知';
        staleWarning = `<div class="market-stale-banner">⚠️ 链上数据采集失败，当前显示 ${staleSince} 的缓存数据</div>`;
    }

    // 表格行：只展示可追踪的供应商
    let rows = '';
    let trackableCount = 0;
    let notTrackableNames = [];
    PROVIDER_ORDER.forEach(id => {
        const d = onchain.providers[id];
        const name = MARKET_PROVIDER_NAMES[id];
        if (!d || d.trackable === false) {
            if (d) notTrackableNames.push(name);
            return;
        }

        if (d.trackable === true || d.trackable === 'partial') {
            trackableCount++;
            const total = d.total_onchain_footprint ?? d.active_wallets_30d;
            if (total == null) {
                rows += `<tr><td>${name}</td><td class="market-na" colspan="3">数据获取失败</td></tr>`;
                return;
            }

            const growthBadge = _renderGrowthBadge(computeGrowthMetrics(d.daily_series));

            if (d.trackable === 'partial') {
                rows += `<tr>
                    <td>${name} <span class="market-partial-badge">上界估计</span></td>
                    <td>≈ ${formatNum(d.erc4337_active_wallets_30d)}</td>
                    <td>—</td>
                    <td class="market-green">≈ ${formatNum(total)}${growthBadge}</td>
                </tr>`;
            } else { // trackable: true (Coinbase, Crossmint precise, etc.)
                rows += `<tr>
                    <td>${name}${d.source === 'rpc_precise' ? ' <span class="market-precise-badge">精准归因</span>' : ''}</td>
                    <td>${formatNum(d.erc4337_active_wallets_30d)}</td>
                    <td>${d.eip7702_live_accounts != null ? formatNum(d.eip7702_live_accounts) : '—'}</td>
                    <td class="market-green">${formatNum(total)}${growthBadge}</td>
                </tr>`;
            }
        }
    });

    // 数据新鲜度
    const freshness = onchain.data_freshness || {};
    const sla = freshness.sla || 'T+1';

    // 不可观测供应商覆盖条
    const notTrackableNote = notTrackableNames.length
        ? `<div class="market-coverage-footnote">不可观测（${notTrackableNames.length}）：${notTrackableNames.join('、')} — 架构原因无法链上归因</div>`
        : '';

    // --- Card 5a: 用户激活汇总 ---
    const card5a = `
    <div class="market-card${onchain.stale ? ' market-card-stale' : ''}">
        <h3 class="market-card-title">可观测用户激活（链上代理）</h3>
        <div class="market-card-subtitle">衡量最近30日新增可用钱包账户，非 DAU/MAU</div>
        <div class="market-coverage-badge">可观测 ${trackableCount}/${PROVIDER_ORDER.length} 供应商</div>
        ${staleWarning}
        <table class="market-table">
            <thead><tr><th>供应商</th><th>智能账户新增</th><th>EOA 授权新增</th><th>30日新增激活（可观测）</th></tr></thead>
            <tbody>${rows}</tbody>
        </table>
        ${notTrackableNote}
        <div class="market-data-month">数据范围：${freshness.series_start || '—'} ~ ${freshness.series_end || '—'} (${freshness.num_days || '—'}d) ｜ 时效：${sla}</div>
        <div class="market-confidence status-pass">覆盖说明：${trackableCount}/${PROVIDER_ORDER.length} 可观测；Coinbase 高置信${onchain.providers?.crossmint?.trackable === true ? '，Crossmint 精准归因（factory+bundler）' : onchain.providers?.crossmint?.trackable === 'partial' ? '，Crossmint 为上界估计' : ''}</div>
    </div>`;

    // --- Card 5b: 链偏好分布 ---
    const chainHtml = renderChainDistribution(onchain);
    const card5b = chainHtml ? `
    <div class="market-card">
        <h3 class="market-card-title">链偏好分布</h3>
        <div class="market-card-subtitle">30 日新增激活在各区块链上的分布对比</div>
        ${chainHtml}
    </div>` : '';

    // --- Card 5c: 日趋势 + 深度分析 ---
    const card5c = `
    <div class="market-card">
        <h3 class="market-card-title">日新增趋势</h3>
        <div class="market-chart-container">
            <canvas id="onchain-daily-chart"></canvas>
        </div>
        <div class="market-card-insight">该指标回答：谁在最近30天持续新增可用钱包账户。不能回答：真实活跃用户数 / 留存率。</div>
        <div class="market-deepdive">
            <div class="market-deepdive-title">🔍 活跃用户深度分析（Dune 看板）</div>
            <div class="market-deepdive-desc">以下看板提供 MAU/DAU、新增 vs 回访用户、留存分布等深度指标：</div>
            <div class="market-deepdive-item">
                <div class="market-deepdive-link">❶ <a href="https://dune.com/wilsoncusack/coinbase-smart-wallet-kpis" target="_blank" rel="noopener">Coinbase Smart Wallet KPIs</a></div>
                <div class="market-deepdive-howto">找 <strong>「Monthly Active Wallets」</strong> = 每月至少发过 1 笔交易的去重钱包数；<strong>「New vs Returning」</strong> 拆分新老用户占比，判断增长质量。</div>
            </div>
            <div class="market-deepdive-item">
                <div class="market-deepdive-link">❷ <a href="https://www.bundlebear.com/erc4337-overview/all" target="_blank" rel="noopener">BundleBear 活跃账户</a></div>
                <div class="market-deepdive-howto">页面顶部 <strong>「Weekly Active Smart Accounts」</strong> = 每周活跃智能账户数；右上角切换链，下方按应用拆分可看 <strong>各家份额</strong>。</div>
            </div>
            <div class="market-deepdive-item">
                <div class="market-deepdive-link">❸ <a href="https://dune.com/niftytable/account-abstraction" target="_blank" rel="noopener">ERC-4337 Account Abstraction</a></div>
                <div class="market-deepdive-howto">找 <strong>「Monthly Active ERC-4337 Smart Accounts」</strong> = 跨链月度活跃总量；另含 <strong>Bundler/Paymaster 市场份额</strong>，观察基础设施竞争格局。</div>
            </div>
        </div>
        <div class="market-upgrade-date">口径升级：2026-03 — 新增 EIP-7702 维度 + 日维度时间序列，schema v4.0</div>
    </div>`;

    return card5a + card5b + card5c;
}

function computeGrowthMetrics(dailySeries) {
    if (!dailySeries || !dailySeries.length) return null;

    // Strip trailing days with total <= 0 (BundleBear partial-day artifacts)
    let series = dailySeries.slice();
    while (series.length && series[series.length - 1].total <= 0) series.pop();
    if (series.length < 8) return null; // need at least 8 days for 7d WoW

    // 7d WoW: last 14 days split into recent_7d / prev_7d
    const tail14 = series.slice(-14);
    const splitAt = Math.max(0, tail14.length - 7);
    const recent7 = tail14.slice(splitAt);
    const prev7 = tail14.slice(Math.max(0, splitAt - 7), splitAt);
    if (!prev7.length || !recent7.length) return null;

    const sumRecent = recent7.reduce((s, p) => s + (p.total || 0), 0);
    const sumPrev = prev7.reduce((s, p) => s + (p.total || 0), 0);
    const wow = sumPrev > 0 ? ((sumRecent - sumPrev) / sumPrev * 100) : null;

    // 30d trend: linear regression slope / mean, threshold ±2%
    let trend = 'flat';
    if (series.length >= 7) {
        const vals = series.map(p => p.total || 0);
        const n = vals.length;
        const mean = vals.reduce((a, b) => a + b, 0) / n;
        if (mean > 0) {
            let sumXY = 0, sumXX = 0;
            for (let i = 0; i < n; i++) {
                sumXY += (i - (n - 1) / 2) * (vals[i] - mean);
                sumXX += (i - (n - 1) / 2) ** 2;
            }
            const slope = sumXX > 0 ? sumXY / sumXX : 0;
            const relSlope = slope / mean * 100;
            if (relSlope > 2) trend = 'up';
            else if (relSlope < -2) trend = 'down';
        }
    }

    return { wow, trend };
}

function _renderGrowthBadge(metrics) {
    if (!metrics) return '';
    let html = '';
    if (metrics.wow !== null) {
        const cls = metrics.wow >= 0 ? 'market-growth-up' : 'market-growth-down';
        const icon = metrics.wow >= 0 ? '▲' : '▼';
        const sign = metrics.wow >= 0 ? '+' : '';
        html += `<div class="market-growth-badge ${cls}">${icon} ${sign}${metrics.wow.toFixed(1)}%<span class="market-growth-label"> 7d</span></div>`;
    }
    if (metrics.trend !== 'flat') {
        const trendCls = metrics.trend === 'up' ? 'market-trend-up' : 'market-trend-down';
        const trendLabel = metrics.trend === 'up' ? '30d 趋势向上' : '30d 趋势向下';
        html += `<div class="market-trend-badge ${trendCls}">${trendLabel}</div>`;
    }
    return html ? `<div class="market-growth-wrap">${html}</div>` : '';
}

function initOnchainDailyChart(onchain) {
    if (!onchain || !onchain.providers) return;
    const canvas = document.getElementById('onchain-daily-chart');
    if (!canvas) return;
    
    const coinbase = onchain.providers.coinbase;
    const crossmint = onchain.providers.crossmint;
    
    if (!coinbase?.daily_series?.length) return;
    
    const labels = coinbase.daily_series.map(p => p.date.slice(5)); // "MM-DD"
    
    const datasets = [];
    
    // Coinbase total (solid line)
    datasets.push({
        label: 'Coinbase 日新增激活（合计）',
        data: coinbase.daily_series.map(p => p.total),
        borderColor: getCssVar('--brand-yellow'),
        backgroundColor: 'transparent',
        borderWidth: 2,
        tension: 0.3,
        pointRadius: 0,
        pointHitRadius: 8,
    });
    
    // Coinbase ERC-4337 (thin dashed)
    datasets.push({
        label: 'Coinbase 智能账户',
        data: coinbase.daily_series.map(p => p.erc4337),
        borderColor: getCssVar('--color-pass'),
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        borderDash: [4, 2],
        tension: 0.3,
        pointRadius: 0,
        pointHitRadius: 8,
    });
    
    // Coinbase EIP-7702 (thin dotted)
    datasets.push({
        label: 'Coinbase EOA 授权',
        data: coinbase.daily_series.map(p => p.eip7702 || 0),
        borderColor: getCssVar('--color-inconclusive'),
        backgroundColor: 'transparent',
        borderWidth: 1.5,
        borderDash: [2, 3],
        tension: 0.3,
        pointRadius: 0,
        pointHitRadius: 8,
    });
    
    // Crossmint (if available)
    if (crossmint?.daily_series?.length) {
        datasets.push({
            label: 'Crossmint ≈上界',
            data: crossmint.daily_series.map(p => p.total),
            borderColor: getCssVar('--color-skip'),
            backgroundColor: 'transparent',
            borderWidth: 1.5,
            borderDash: [6, 3],
            tension: 0.3,
            pointRadius: 0,
            pointHitRadius: 8,
        });
    }

    new Chart(canvas, {
        type: 'line',
        data: { labels, datasets },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: {
                    display: true,
                    position: 'bottom',
                    labels: {
                        color: getCssVar('--text-secondary'),
                        font: { size: 11, family: getCssVar('--font-body') },
                        boxWidth: 20,
                        padding: 12,
                    }
                },
                tooltip: {
                    backgroundColor: getCssVar('--bg-elevated'),
                    titleColor: getCssVar('--text-primary'),
                    bodyColor: getCssVar('--text-secondary'),
                    borderColor: getCssVar('--bg-border'),
                    borderWidth: 1,
                    callbacks: {
                        label: function(ctx) {
                            return ctx.dataset.label + ': ' + ctx.parsed.y.toLocaleString('en-US');
                        }
                    }
                }
            },
            scales: {
                x: {
                    ticks: { color: getCssVar('--text-tertiary'), font: { size: 10 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 10 },
                    grid: { color: 'rgba(255,255,255,0.04)' },
                },
                y: {
                    ticks: {
                        color: getCssVar('--text-tertiary'),
                        font: { size: 10 },
                        callback: function(v) { return v >= 1000 ? (v/1000).toFixed(0) + 'k' : v; }
                    },
                    grid: { color: 'rgba(255,255,255,0.04)' },
                }
            }
        }
    });
}


const CHAIN_COLORS = {
    base: '#0052FF', ethereum: '#627EEA', arbitrum: '#28A0F0',
    optimism: '#FF0420', polygon: '#8247E5',
};
const CHAIN_NAMES = {
    base: 'Base', ethereum: 'Ethereum', arbitrum: 'Arbitrum',
    optimism: 'Optimism', polygon: 'Polygon',
};
const CHAIN_PIE_PROVIDERS = ['coinbase', 'crossmint'];
const CHAIN_PIE_NAMES = { coinbase: 'Coinbase', crossmint: 'Crossmint' };

function renderChainDistribution(onchain) {
    if (!onchain || !onchain.providers) return '';

    let chartsHtml = '';
    let hasData = false;
    let footnotes = [];

    for (const pid of CHAIN_PIE_PROVIDERS) {
        const p = onchain.providers[pid];
        if (!p || !p.chain_distribution) continue;
        const dist = p.chain_distribution;
        const total = Object.values(dist).reduce((a, b) => a + b, 0);
        if (total <= 0) continue;
        hasData = true;

        const entries = Object.entries(dist).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);

        // Build custom HTML legend (Chart.js legend color is unreliable on dark bg)
        let legendHtml = '';
        for (const [chain, count] of entries) {
            const pct = (count / total * 100).toFixed(1);
            const color = CHAIN_COLORS[chain] || '#888';
            const name = CHAIN_NAMES[chain] || chain;
            legendHtml += `
            <div class="chain-legend-row">
                <span class="chain-legend-dot" style="background:${color}"></span>
                <span class="chain-legend-name">${name}</span>
                <span class="chain-legend-pct">${pct}%</span>
                <span class="chain-legend-val">${formatNum(count)}</span>
            </div>`;
        }

        if (p.chain_distribution_source === 'nonce_ratio') {
            footnotes.push(`${CHAIN_PIE_NAMES[pid]} 链分布基于 bundler nonce 累计比例估算`);
        }

        chartsHtml += `
        <div class="market-chain-pie-item">
            <div class="market-chain-pie-header">${CHAIN_PIE_NAMES[pid]}</div>
            <div class="market-chain-pie-total">${formatNum(total)} 总激活</div>
            <div class="market-chain-pie-body">
                <div class="market-chain-pie-canvas"><canvas id="chain-pie-${pid}"></canvas></div>
                <div class="market-chain-pie-legend">${legendHtml}</div>
            </div>
        </div>`;
    }

    if (!hasData) return '';

    const footHtml = footnotes.length
        ? `<div class="market-chain-footnote">${footnotes.join('；')}</div>` : '';

    return `
    <div class="market-chain-pie-row">${chartsHtml}</div>
    ${footHtml}`;
}

function initChainPieCharts(onchain) {
    if (!onchain || !onchain.providers) return;

    for (const pid of CHAIN_PIE_PROVIDERS) {
        const p = onchain.providers[pid];
        if (!p || !p.chain_distribution) continue;
        const canvas = document.getElementById(`chain-pie-${pid}`);
        if (!canvas) continue;

        const entries = Object.entries(p.chain_distribution)
            .filter(([, v]) => v > 0)
            .sort((a, b) => b[1] - a[1]);
        if (!entries.length) continue;

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: entries.map(([chain]) => CHAIN_NAMES[chain] || chain),
                datasets: [{
                    data: entries.map(([, v]) => v),
                    backgroundColor: entries.map(([chain]) => CHAIN_COLORS[chain] || '#888'),
                    borderWidth: 0,
                    hoverOffset: 6,
                }],
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                cutout: '58%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: '#1E2329',
                        titleColor: '#EAECEF',
                        bodyColor: '#B7BDC6',
                        borderColor: '#2B3139',
                        borderWidth: 1,
                        callbacks: {
                            label: function(ctx) {
                                const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                const pct = (ctx.parsed / total * 100).toFixed(1);
                                return ` ${ctx.label}: ${ctx.parsed.toLocaleString('en-US')} (${pct}%)`;
                            },
                        },
                    },
                },
            },
        });
    }
}

function renderMarketFreshness(npm, pypi, github, status, docs, onchain) {
    const sources = [npm, pypi, github, status, docs, onchain].filter(Boolean);
    if (sources.length === 0) return '<div class="market-freshness">数据更新时间未知</div>';

    const timestamps = sources.map(s => s.collected_at).filter(Boolean).map(t => new Date(t).getTime());
    if (timestamps.length === 0) return '<div class="market-freshness">数据更新时间未知</div>';

    const oldest = Math.min(...timestamps);
    const oldestDate = new Date(oldest);
    const yyyy = oldestDate.getUTCFullYear();
    const mm = String(oldestDate.getUTCMonth() + 1).padStart(2, '0');
    const dd = String(oldestDate.getUTCDate()).padStart(2, '0');
    const hh = String(oldestDate.getUTCHours()).padStart(2, '0');
    const mi = String(oldestDate.getUTCMinutes()).padStart(2, '0');
    const dateStr = `${yyyy}-${mm}-${dd} ${hh}:${mi} UTC`;

    const ageMs = Date.now() - oldest;
    const isStale = ageMs > 48 * 60 * 60 * 1000;
    const staleWarning = isStale ? ' <span class="market-stale-warn">⚠️ 数据可能已过期</span>' : '';

    return `<div class="market-freshness">数据更新于 ${dateStr}${staleWarning}</div>`;
}

document.addEventListener("DOMContentLoaded", () => {
    loadData();

    // --- Mobile sidebar toggle ---
    const menuToggle = document.getElementById('menu-toggle');
    const viewTabs = document.getElementById('view-tabs');
    const navBackdrop = document.getElementById('nav-backdrop');

    function closeSidebar() {
        viewTabs.classList.remove('open');
        menuToggle.classList.remove('open');
        navBackdrop.classList.remove('visible');
    }

    menuToggle.addEventListener('click', () => {
        const isOpen = viewTabs.classList.toggle('open');
        menuToggle.classList.toggle('open', isOpen);
        navBackdrop.classList.toggle('visible', isOpen);
    });
    navBackdrop.addEventListener('click', closeSidebar);

    // Top-level tab clicks
    document.querySelectorAll("#view-tabs > .tab").forEach(tab => {
        tab.addEventListener("click", () => {
            closeSidebar();
            switchTab(tab.dataset.view);
        });
    });
    // Sub-tab clicks
    document.querySelectorAll(".sub-tab").forEach(tab => {
        tab.addEventListener("click", () => switchTab(tab.dataset.sub));
    });
    document.getElementById("close-detail").addEventListener("click", closeDetail);
    window.addEventListener('hashchange', handleRouting);
});

// --------------------------------------------------------------------------
// Markdown article renderer (for docs tabs)
// --------------------------------------------------------------------------
function renderMarkdownTab(containerId, mdPath) {
    const container = document.getElementById(containerId);
    if (!container || container.dataset.rendered) return;
    container.dataset.rendered = '1';

    fetch(mdPath)
        .then(r => {
            if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
            return r.text();
        })
        .then(md => {
            container.innerHTML = '<div class="wt-article">' + marked.parse(md) + '</div>';
        })
        .catch(err => {
            container.innerHTML = `<p class="loading">加载失败：${err.message}</p>`;
        });
}
