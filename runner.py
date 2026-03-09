"""wallet-bench runner — test orchestration with safety guards.

Usage:
    python runner.py run --provider bnbchain_mcp --config config.yaml
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from adapters.base import TestResult, TestStatus
from cases.registry import discover

_ROOT = Path(__file__).resolve().parent
_RESULTS_DIR = _ROOT / "results"

# Auto-load .env if present (OKX keys, etc.); won't override existing env vars
load_dotenv(_ROOT / ".env", override=False)

# ---------------------------------------------------------------------------
# Safety: redaction patterns
# ---------------------------------------------------------------------------

_REDACT_PATTERNS: list[re.Pattern[str]] = [
    # Private keys (64 hex chars after 0x)
    re.compile(r"0x[0-9a-fA-F]{64}"),
    # Ethereum addresses (40 hex chars after 0x)
    re.compile(r"0x[0-9a-fA-F]{40}"),
    # Bearer tokens
    re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE),
    # Generic API key patterns
    re.compile(r"(?:api[_-]?key|apikey|secret)[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9\-._~+/]{16,})", re.IGNORECASE),
]

_REDACT_PLACEHOLDER = "[REDACTED]"


def _redact(text: str) -> str:
    for pat in _REDACT_PATTERNS:
        text = pat.sub(_REDACT_PLACEHOLDER, text)
    return text


def _redact_obj(obj: Any) -> Any:
    """Recursively redact sensitive strings in a JSON-serialisable object."""
    if isinstance(obj, str):
        return _redact(obj)
    if isinstance(obj, dict):
        return {k: _redact_obj(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_redact_obj(v) for v in obj]
    return obj

# ---------------------------------------------------------------------------
# Test taxonomy: category + architecture applicability (ISSUE-006 AC-016)
# ---------------------------------------------------------------------------

# Maps test_name → category.  Tests not listed default to 'infra'.
TEST_CATEGORY: dict[str, str] = {
    # 钱包基础 (wallet_core)
    'key_generate': 'wallet_core',
    'sign_message': 'wallet_core',
    'sign_typed_data': 'wallet_core',
    'send_tx': 'wallet_core',
    'multi_chain': 'wallet_core',
    'preflight_fee': 'wallet_core',
    'nonce_management': 'wallet_core',
    'tx_confirmation': 'wallet_core',
    'erc20_transfer': 'wallet_core',
    'contract_write': 'wallet_core',
    # 权限治理 (governance)
    # 'policy_enforcement': 'governance',  # Removed: enterprise-grade feature, see Privy evaluation notes
    'session_delegation': 'governance',
    'authorization_audit_trace': 'governance',
    # 'policy_revocation_latency': 'governance',  # Removed: depends on policy_enforcement
    'denial_reason_quality': 'governance',
    # 稳定性 (reliability)
    'concurrent_ops': 'reliability',
    'failure_recovery': 'reliability',
    'rate_limit_resilience': 'reliability',
    'idempotent_submit': 'reliability',
    'retry_backoff': 'reliability',
    'tx_finality': 'reliability',
    # 运维能力 (ops)
    'portability_recovery': 'ops',
    'derivation_path': 'ops',
    'keychain_lock': 'ops',
    'backup_recovery': 'ops',
    'webhook_delivery': 'ops',
    'quota_disclosure': 'ops',
    # ops - class-specific (intent/tee)
    'intent_schema': 'ops',
    'fulfillment_sla': 'ops',
    'cancellation': 'ops',
    'attestation': 'ops',
    'failover_continuity': 'ops',
    'policy_depth': 'ops',
    # 应用能力 (app)
    'token_swap': 'app',
    'defi_interaction': 'app',
    'cross_chain_bridge': 'app',
    'prediction_market': 'app',
    'perps_trading': 'app',
    # 安全性 (security)
    'sig_verify': 'security',
    # Agent 可用性 (agent)
    'schema_quality': 'agent',
    'machine_errors': 'agent',
    'deterministic_response': 'agent',
    'timeout_sla': 'reliability',
    'idempotency_key': 'reliability',
    'soak_24h': 'ops',
    'version_compat': 'ops',
    'token_cost': 'agent',
    'multi_step_recovery': 'agent',
    # Observation-only stubs (ISSUE-021 Phase 3)
    'policy_method_scope': 'governance',
    'rbac': 'governance',
    'approval_workflow': 'governance',
    'audit_export': 'ops',
    'secret_rotation': 'security',
    # ISSUE-025: Swap 场景扩充
    'route_discovery': 'app',
    'slippage_guard': 'app',
    'mev_protection': 'app',
    'minimal_approve': 'app',
    'post_revoke': 'app',
    'unsafe_approve_detect': 'app',
    # ISSUE-025: DeFi/跨链/预测市场组合
    'farm_combo': 'app',
    'arb_atomicity': 'app',
    'market_combo': 'app',
    # ISSUE-025: Agent 自主性扩充
    'tool_discovery': 'agent',
    'zero_shot_exec': 'agent',
    'error_self_recovery': 'agent',
    'multi_step_plan': 'agent',
    'context_efficiency': 'agent',
    'fc_compatibility': 'agent',
    # ISSUE-025: 性能基准
    'tx_latency': 'reliability',
    'burst_throughput': 'reliability',
    'cold_start': 'reliability',
    'gas_accuracy': 'reliability',
    'mempool_latency': 'reliability',
    'bridge_completion': 'reliability',
}

# Providers without built-in app-layer actions (swap/DeFi/bridge etc.).
# They CAN support DeFi via raw send_transaction + calldata — see DeFi matrix.
# Marked N/A here because the *benchmark test* checks for built-in high-level APIs.
NO_BUILTIN_APP_PROVIDERS: set[str] = {'bnbchain_mcp', 'crossmint', 'privy', 'para_wallet'}

# Backward compat alias
INFRA_PROVIDERS = NO_BUILTIN_APP_PROVIDERS

# Maps test_name → source classification for AC-008-C5
TEST_SOURCE: dict[str, str] = {
    # auto: fully automated by runner
    'key_generate': 'auto', 'sign_message': 'auto', 'sign_typed_data': 'auto',
    'send_tx': 'auto', 'multi_chain': 'auto', 'preflight_fee': 'auto',
    'nonce_management': 'auto', 'tx_confirmation': 'auto',
    'session_delegation': 'auto', 'authorization_audit_trace': 'auto',
    'denial_reason_quality': 'auto',
    'concurrent_ops': 'auto', 'failure_recovery': 'auto',
    'rate_limit_resilience': 'auto', 'idempotent_submit': 'auto', 'retry_backoff': 'auto',
    'portability_recovery': 'auto', 'webhook_delivery': 'auto', 'quota_disclosure': 'auto',
    'derivation_path': 'auto', 'keychain_lock': 'auto', 'backup_recovery': 'auto',
    'intent_schema': 'auto', 'fulfillment_sla': 'auto', 'cancellation': 'auto',
    'attestation': 'auto', 'failover_continuity': 'auto', 'policy_depth': 'auto',
    # hybrid: runner + human evaluation
    'token_swap': 'hybrid', 'defi_interaction': 'hybrid',
    'cross_chain_bridge': 'hybrid', 'prediction_market': 'hybrid', 'perps_trading': 'hybrid',
    # Phase 1 P0: new automated tests (ISSUE-021)
    'erc20_transfer': 'auto', 'contract_write': 'auto', 'sig_verify': 'auto',
    'tx_finality': 'auto',
    'schema_quality': 'auto', 'machine_errors': 'auto', 'deterministic_response': 'auto',
    # Phase 3: new automated tests (ISSUE-021)
    'timeout_sla': 'auto', 'idempotency_key': 'auto',
    'soak_24h': 'auto', 'version_compat': 'auto',
    'token_cost': 'auto', 'multi_step_recovery': 'auto',
    # Observation-only stubs (ISSUE-021 Phase 3)
    'policy_method_scope': 'auto', 'rbac': 'auto', 'approval_workflow': 'auto',
    'audit_export': 'auto', 'secret_rotation': 'auto',
    # ISSUE-025: Swap（hybrid — 需要真实执行验证）
    'route_discovery': 'hybrid', 'slippage_guard': 'hybrid', 'mev_protection': 'hybrid',
    'minimal_approve': 'hybrid', 'post_revoke': 'hybrid', 'unsafe_approve_detect': 'hybrid',
    # ISSUE-025: 场景组合（hybrid）
    'farm_combo': 'hybrid', 'arb_atomicity': 'hybrid', 'market_combo': 'hybrid',
    # ISSUE-025: Agent（auto）
    'tool_discovery': 'auto', 'zero_shot_exec': 'auto', 'error_self_recovery': 'auto',
    'multi_step_plan': 'auto', 'context_efficiency': 'auto', 'fc_compatibility': 'auto',
    # ISSUE-025: 性能（auto）
    'tx_latency': 'auto', 'burst_throughput': 'auto', 'cold_start': 'auto',
    'gas_accuracy': 'auto', 'mempool_latency': 'auto', 'bridge_completion': 'auto',
}


# Architecture-specific tests that only apply to 'local' class providers.
# Non-local providers get N/A for these (architecture_mismatch).
ARCH_LOCAL_ONLY_TESTS: set[str] = {'derivation_path', 'keychain_lock', 'backup_recovery'}

# Architecture-specific tests that only apply to 'tee' class providers (ISSUE-028).
ARCH_TEE_ONLY_TESTS: set[str] = {'attestation', 'failover_continuity', 'policy_depth'}

# Architecture-specific tests that only apply to 'intent' class providers (ISSUE-028).
ARCH_INTENT_ONLY_TESTS: set[str] = {'intent_schema', 'fulfillment_sla', 'cancellation'}
# Non-local providers get N/A for these (architecture_mismatch).

# Human-readable N/A messages per skip_reason
_NA_MESSAGES: dict[str, str] = {
    'category_mismatch': (
        '该供应商无内置应用层 API（如 Swap/DeFi），但可通过 send_transaction + calldata 实现。'
        '详见 DeFi 集成矩阵。'
    ),
    'architecture_mismatch': '该测试仅适用于 local 架构的供应商。',
    'architecture_mismatch_tee': '该测试仅适用于 TEE 架构的供应商（可信执行环境）。',
    'architecture_mismatch_intent': '该测试仅适用于 Intent 架构的供应商。',
}

def _is_not_applicable(provider_name: str, arch_class: str, test_name: str) -> str | None:
    """Return skip_reason if the test is not applicable, else None."""
    category = TEST_CATEGORY.get(test_name, 'wallet_core')
    # Providers without built-in app-layer API
    if category == 'app' and provider_name in NO_BUILTIN_APP_PROVIDERS:
        return 'category_mismatch'
    # Non-local providers cannot run local-only arch tests
    if test_name in ARCH_LOCAL_ONLY_TESTS and arch_class != 'local':
        return 'architecture_mismatch'
    # Non-tee providers cannot run tee-only arch tests (ISSUE-028)
    if test_name in ARCH_TEE_ONLY_TESTS and arch_class != 'tee':
        return 'architecture_mismatch_tee'
    # Non-intent providers cannot run intent-only arch tests (ISSUE-028)
    if test_name in ARCH_INTENT_ONLY_TESTS and arch_class != 'intent':
        return 'architecture_mismatch_intent'
    return None

# ---------------------------------------------------------------------------
# Safety: network guards
# ---------------------------------------------------------------------------

def _validate_network(config: dict) -> None:
    """Abort if config references a blocked chain ID or disallowed network."""
    safety = config.get("safety", {})
    blocked_ids = set(safety.get("blocked_chain_ids", []))
    allowed_nets = set(safety.get("allowed_networks", []))

    for pname, pcfg in config.get("providers", {}).items():
        if isinstance(pcfg, dict):
            network = pcfg.get("network", "")
            if network and allowed_nets and network not in allowed_nets:
                print(f"ABORT: provider '{pname}' uses network '{network}' which is not in allowed_networks", file=sys.stderr)
                sys.exit(1)

            chain_id = pcfg.get("chain_id")
            if chain_id and int(chain_id) in blocked_ids:
                print(f"ABORT: provider '{pname}' uses blocked chain_id {chain_id}", file=sys.stderr)
                sys.exit(1)


def _validate_rpc(config: dict) -> None:
    """Check any RPC URLs against allowlist."""
    allowlist = set(config.get("safety", {}).get("rpc_allowlist", []))
    if not allowlist:
        return
    for pname, pcfg in config.get("providers", {}).items():
        if isinstance(pcfg, dict):
            rpc = pcfg.get("rpc_url", "")
            if rpc and rpc not in allowlist:
                print(f"ABORT: provider '{pname}' uses RPC '{rpc}' not in allowlist", file=sys.stderr)
                sys.exit(1)


# ---------------------------------------------------------------------------
# Adapter loader
# ---------------------------------------------------------------------------

def _load_adapter(provider_name: str, config: dict):
    """Dynamically import and instantiate the adapter for a provider."""
    provider_yaml = _ROOT / "providers" / f"{provider_name}.yaml"
    if not provider_yaml.exists():
        print(f"ERROR: provider file not found: {provider_yaml}", file=sys.stderr)
        sys.exit(1)

    with open(provider_yaml) as f:
        provider_meta = yaml.safe_load(f)

    arch_class = provider_meta.get("class", "")
    provider_cfg = config.get("providers", {}).get(provider_name, {})

    # Import adapter module
    mod = __import__(f"adapters.{provider_name}", fromlist=[provider_name])

    # Find the adapter class (first subclass of WalletAdapter in the module)
    from adapters.base import WalletAdapter
    adapter_cls: Any = None
    for attr_name in dir(mod):
        attr = getattr(mod, attr_name)
        if isinstance(attr, type) and issubclass(attr, WalletAdapter) and attr is not WalletAdapter:
            adapter_cls = attr
            break

    if adapter_cls is None:
        print(f"ERROR: no WalletAdapter subclass found in adapters.{provider_name}", file=sys.stderr)
        sys.exit(1)

    # Instantiate with provider config
    if provider_name == "bnbchain_mcp":
        adapter = adapter_cls(
            private_key=provider_cfg.get("private_key", ""),
            network=provider_cfg.get("network", "bsc-testnet"),
        )
    elif provider_name == "crossmint":
        adapter = adapter_cls(
            api_key=provider_cfg.get("api_key", ""),
            chain=provider_cfg.get("chain", "base-sepolia"),
            eoa_private_key=provider_cfg.get("eoa_private_key", ""),
        )
    elif provider_name == "crossmint_mcp":
        adapter = adapter_cls(
            api_key=provider_cfg.get("api_key", ""),
            agent_wallet_address=provider_cfg.get("agent_wallet_address", ""),
            server_path=provider_cfg.get("server_path", ""),
            recipient_email=provider_cfg.get("recipient_email", "bench@example.com"),
            recipient_name=provider_cfg.get("recipient_name", "Wallet Bench"),
        )
    elif provider_name == "coinbase_agentkit":
        adapter = adapter_cls(
            cdp_key_file=provider_cfg.get("cdp_key_file", "cdp_api_key.json"),
            network_id=provider_cfg.get("network_id", "base-sepolia"),
            wallet_secret=provider_cfg.get("wallet_secret", ""),
        )
    elif provider_name == "privy":
        adapter = adapter_cls(
            app_id=provider_cfg.get("app_id", ""),
            app_secret=provider_cfg.get("app_secret", ""),
            chain=provider_cfg.get("chain", "ethereum-sepolia"),
            wallet_id=provider_cfg.get("wallet_id", ""),
        )
    elif provider_name == "moonpay":
        adapter = adapter_cls(
            wallet_name=provider_cfg.get("wallet_name", "bench"),
            chain=provider_cfg.get("chain", "ethereum"),
        )
    elif provider_name == "minara":
        adapter = adapter_cls(
            chain=provider_cfg.get("chain", "base"),
        )
    elif provider_name == "universal_trading":
        adapter = adapter_cls(
            repo_path=provider_cfg.get("repo_path", "universal-account-example"),
            chain=provider_cfg.get("chain", "bsc"),
        )
    elif provider_name == "polymarket_agent":
        adapter = adapter_cls(
            chain=provider_cfg.get("chain", "polygon"),
        )
    elif provider_name == "coinpilot_hyperliquid":
        adapter = adapter_cls(
            config_path=provider_cfg.get("config_path", "coinpilot.json"),
            api_base_url=provider_cfg.get("api_base_url", ""),
        )
    elif provider_name == "okx_onchainos":
        adapter = adapter_cls(
            address=provider_cfg.get("address", ""),
            chain=provider_cfg.get("chain", "ethereum"),
        )
    elif provider_name == "clawlett":
        adapter = adapter_cls(
            safe_address=provider_cfg.get("safe_address", ""),
            agent_key=provider_cfg.get("agent_key", ""),
            owner_address=provider_cfg.get("owner_address", ""),
            clawlett_repo_path=provider_cfg.get("clawlett_repo_path", ""),
        )
    elif provider_name == "para_wallet":
        adapter = adapter_cls(
            api_key=provider_cfg.get("api_key", ""),
            base_url=provider_cfg.get("base_url", "https://api.beta.getpara.com"),
            user_identifier=provider_cfg.get("user_identifier", "wallet-bench@test.com"),
            chain=provider_cfg.get("chain", "ethereum"),
        )
    else:
        adapter = adapter_cls(**provider_cfg)

    return adapter, arch_class, provider_meta


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

async def _run_tests(provider_name: str, config: dict, runs: int = 1) -> dict[str, Any]:
    adapter, arch_class, provider_meta = _load_adapter(provider_name, config)
    test_specs = discover(arch_class, include_all_classes=True)  # ISSUE-028: include all arch tests for N/A marking

    print(f"Provider: {provider_meta.get('name', provider_name)}")
    print(f"Class: {arch_class}")
    print(f"Tests discovered: {len(test_specs)}")
    if runs > 1:
        print(f"Runs per test: {runs} (median of successes)")
    print()

    await adapter.setup()
    results: list[dict[str, Any]] = []

    try:
        for spec in test_specs:
            # --- N/A pre-check (AC-006-16) ---
            na_reason = _is_not_applicable(provider_name, arch_class, spec.test_name)
            if na_reason is not None:
                print(f"  [{spec.test_id}] {spec.test_name} ({spec.source}) ... NOT_APPLICABLE ({na_reason})")
                na_result = TestResult(
                    test_id=spec.test_id,
                    test_name=spec.test_name,
                    status=TestStatus.NOT_APPLICABLE,
                    message=_NA_MESSAGES.get(na_reason, na_reason),
                )
                rec = na_result.model_dump()
                rec['skip_reason'] = na_reason
                rec['source'] = TEST_SOURCE.get(spec.test_name, 'auto')
                results.append(rec)
                continue

            if runs == 1:
                # Single run — original behavior
                print(f"  [{spec.test_id}] {spec.test_name} ({spec.source}) ... ", end="", flush=True)
                try:
                    result = await spec.run(adapter, config)
                except BaseException as exc:
                    result = TestResult(
                        test_id=spec.test_id,
                        test_name=spec.test_name,
                        status=TestStatus.ERROR,
                        message=str(exc),
                    )
                print(f"{result.status.value.upper()} ({result.elapsed_ms:.0f}ms)")
                rec = result.model_dump()
                rec['source'] = TEST_SOURCE.get(spec.test_name, 'auto')
                results.append(rec)
            else:
                # Multi-run — collect N samples, compute latency stats from successes
                print(f"  [{spec.test_id}] {spec.test_name} ({spec.source}) x{runs} ... ", end="", flush=True)
                run_results: list[TestResult] = []
                for i in range(runs):
                    try:
                        r = await spec.run(adapter, config)
                    except BaseException as exc:
                        r = TestResult(
                            test_id=spec.test_id,
                            test_name=spec.test_name,
                            status=TestStatus.ERROR,
                            message=str(exc),
                        )
                    run_results.append(r)

                # Pick representative result: prefer pass, then skip, then first
                success_runs = [r for r in run_results if r.status == TestStatus.PASS]
                skip_runs = [r for r in run_results if r.status == TestStatus.SKIP]
                representative = (success_runs or skip_runs or run_results)[0]

                # Compute latency stats from successful (non-zero elapsed) runs only
                success_latencies = [r.elapsed_ms for r in success_runs if r.elapsed_ms > 0]
                rec = representative.model_dump()
                if success_latencies:
                    rec["latency"] = {
                        "median": round(statistics.median(success_latencies), 1),
                        "min": round(min(success_latencies), 1),
                        "max": round(max(success_latencies), 1),
                        "runs_count": len(success_latencies),
                    }
                    rec["elapsed_ms"] = rec["latency"]["median"]  # backward compat
                else:
                    rec["latency"] = {
                        "median": 0,
                        "min": 0,
                        "max": 0,
                        "runs_count": 0,
                    }

                pass_count = len(success_runs)
                total_count = len(run_results)
                median_ms = rec["latency"]["median"]
                print(f"{representative.status.value.upper()} ({pass_count}/{total_count} pass, median {median_ms:.0f}ms)")
                rec['source'] = TEST_SOURCE.get(spec.test_name, 'auto')
                results.append(rec)

                # Session recovery: cold_start may kill the adapter session
                if spec.test_name == 'cold_start' and pass_count == 0:
                    try:
                        await adapter.teardown()
                    except BaseException:
                        pass
                    try:
                        await adapter.setup()
                        print("  [info] adapter re-setup after cold_start")
                    except BaseException as exc:
                        print(f"  [warn] adapter re-setup failed: {exc}")
    finally:
        try:
            await adapter.teardown()
        except BaseException as exc:
            print(f"\n  [warn] teardown error (non-fatal): {type(exc).__name__}: {exc}")

    # Load DX evaluation if available
    eval_path = _ROOT / "evaluations" / f"{provider_name}.yaml"
    evaluation = None
    if eval_path.exists():
        with open(eval_path) as f:
            evaluation = yaml.safe_load(f)

    run_record = {
        "provider": provider_name,
        "provider_meta": provider_meta,
        "capabilities": adapter.capabilities(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "evaluation": evaluation,
    }
    return run_record


def _write_results(run_record: dict[str, Any]) -> None:
    _RESULTS_DIR.mkdir(exist_ok=True)
    provider_name = run_record.get("provider", "unknown")

    # Private debug — per-provider file
    private_path = _RESULTS_DIR / f"private_debug_{provider_name}.json"
    with open(private_path, "w") as f:
        json.dump(run_record, f, indent=2, default=str)
    print(f"\nPrivate results: {private_path}")

    # Public results — aggregate all providers into one file
    public_record = _redact_obj(run_record)
    public_path = _RESULTS_DIR / "public_results.json"

    # Load existing aggregate data
    existing: dict[str, Any] = {"providers": []}
    if public_path.exists():
        try:
            with open(public_path) as f:
                data = json.load(f)
            # Handle both old single-provider format and new aggregate format
            if "providers" in data and isinstance(data["providers"], list):
                existing = data
            elif "provider" in data:
                existing = {"providers": [data]}
        except (json.JSONDecodeError, KeyError):
            pass

    # Replace existing entry for this provider, or append
    providers = [p for p in existing["providers"] if p.get("provider") != provider_name]
    providers.append(public_record)
    providers.sort(key=lambda p: p.get("provider", ""))

    output = {
        "providers": providers,
        "summary": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provider_count": len(providers),
        },
    }
    with open(public_path, "w") as f:
        json.dump(output, f, indent=2, default=str)
    print(f"Public results:  {public_path} ({len(providers)} providers)")


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def _print_summary(run_record: dict[str, Any]) -> None:
    results = run_record["results"]
    total = len(results)
    passed = sum(1 for r in results if r["status"] == "pass")
    failed = sum(1 for r in results if r["status"] == "fail")
    skipped = sum(1 for r in results if r["status"] == "skip")
    errors = sum(1 for r in results if r["status"] == "error")
    na = sum(1 for r in results if r["status"] == "not_applicable")
    unsupported = sum(1 for r in results if r["status"] == "unsupported")
    inconclusive = sum(1 for r in results if r["status"] == "inconclusive")

    # Scorable = pass + fail + error + unsupported (provider responsibility)
    # Excluded: skip (industry blank), inconclusive (benchmark gap), not_applicable (arch)
    scored = passed + failed + errors + unsupported
    coverage_pct = (scored / total * 100) if total > 0 else 0
    score_pct = (passed / scored * 100) if scored > 0 else 0

    print(f"\n{'='*76}")
    parts = [f"PASS: {passed}", f"FAIL: {failed}"]
    if unsupported:
        parts.append(f"UNSUPPORTED: {unsupported}")
    if inconclusive:
        parts.append(f"INCONCLUSIVE: {inconclusive}")
    if skipped:
        parts.append(f"SKIP: {skipped}")
    parts.extend([f"ERROR: {errors}", f"N/A: {na}", f"TOTAL: {total}"])
    print(f"  {'  '.join(parts)}")
    print(f"  Score: {score_pct:.1f}% ({passed}/{scored} scored)  Coverage: {coverage_pct:.0f}% ({scored}/{total})")
    print(f"{'='*76}")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="wallet-bench runner")
    sub = parser.add_subparsers(dest="command")

    run_p = sub.add_parser("run", help="Run benchmark tests")
    run_p.add_argument("--provider", required=True, help="Provider name (e.g. bnbchain_mcp)")
    run_p.add_argument("--config", required=True, help="Path to config.yaml")
    run_p.add_argument("--runs", type=int, default=1, help="Number of runs per test (default: 1). Median of successes is used.")

    args = parser.parse_args()
    if args.command != "run":
        parser.print_help()
        sys.exit(1)

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Safety checks
    _validate_network(config)
    _validate_rpc(config)

    run_record = asyncio.run(_run_tests(args.provider, config, runs=args.runs))
    _write_results(run_record)
    _print_summary(run_record)


if __name__ == "__main__":
    main()
