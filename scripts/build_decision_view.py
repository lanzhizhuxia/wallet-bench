#!/usr/bin/env python3
"""Build decision_view.v1.json for the wallet-bench dashboard.

Reads:
  - docs/data/defi_matrix.v1.json (DeFi integration cost matrix)
  - results/public_results.json   (technical benchmark results, optional)

Writes:
  - web/data/decision_view.v1.json (merged view for frontend consumption)

Usage:
  python3 scripts/build_decision_view.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFI_MATRIX_PATH = REPO_ROOT / "docs" / "data" / "defi_matrix.v1.json"
TECH_RESULTS_PATH = REPO_ROOT / "results" / "public_results.json"
OUTPUT_PATH = REPO_ROOT / "web" / "data" / "decision_view.v1.json"

# Display names for weight presets (data only has machine keys)
_PRESET_NAMES: dict[str, str] = {
    "equal": "等权 (Equal)",
    "defi_heavy": "DeFi 为重",
    "trading_heavy": "交易为重",
}



def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def compute_tech_scores(tech_data: dict | None) -> dict:
    """Extract per-provider technical scores from public_results.json."""
    if not tech_data:
        return {}

    providers = tech_data.get("providers", [])
    if not providers:
        providers = [tech_data] if "provider" in tech_data else []

    scores = {}
    for p in providers:
        pid = p.get("provider", "")
        results = p.get("results", [])
        passed = sum(1 for r in results if r.get("status") == "pass")
        failed = sum(1 for r in results if r.get("status") == "fail")
        unsup = sum(1 for r in results if r.get("status") == "unsupported")
        incon = sum(1 for r in results if r.get("status") == "inconclusive")
        total = len(results)
        denom = passed + failed + unsup
        scores[pid] = {
            "score": round(passed / denom * 100, 1) if denom > 0 else 0,
            "confidence": round((total - incon) / total * 100, 1) if total > 0 else 0,
            "pass": passed,
            "fail": failed,
            "unsupported": unsup,
            "inconclusive": incon,
            "total": total,
        }
    return scores


def compute_defi_scores(defi_data: dict) -> dict:
    """Compute DeFi scores per provider under each weight preset."""
    rating_defs = defi_data["rating_definitions"]
    proxy_map = {k: v["numeric_proxy"] for k, v in rating_defs.items()}
    weight_presets = defi_data["weight_presets"]
    ratings = defi_data["ratings"]

    result = {}
    for pid, provider_ratings in ratings.items():
        provider_scores = {}
        for preset_name, weights in weight_presets.items():
            total = 0
            for scenario_id, weight in weights.items():
                rating_key = provider_ratings[scenario_id]["rating"]
                proxy = proxy_map.get(rating_key, 0)
                total += proxy * weight
            provider_scores[preset_name] = round(total * 100, 1)
        
        # Per-scenario proxy values
        scenario_proxies = {}
        for scenario_id, r in provider_ratings.items():
            entry = {
                "rating": r["rating"],
                "label": rating_defs[r["rating"]]["label"],
                "emoji": rating_defs[r["rating"]]["emoji"],
                "proxy": proxy_map.get(r["rating"], 0),
                "integration_mode": r.get("integration_mode", ""),
                "tx_steps": r.get("tx_steps"),
                "external_deps": r.get("external_deps", []),
                "human_intervention": r.get("human_intervention"),
                "rationale": r.get("rationale", ""),
                "confidence": r.get("confidence", "high"),
                "caveats": r.get("caveats", []),
            }
            scenario_proxies[scenario_id] = entry
        
        coverage = sum(
            1 for r in provider_ratings.values() 
            if r["rating"] not in ("not_feasible",)
        )
        
        result[pid] = {
            "scores": provider_scores,
            "scenarios": scenario_proxies,
            "coverage": f"{coverage}/4",
        }
    return result


def build_use_case_recommendations(defi_scores: dict, tech_scores: dict) -> list:
    """Generate per-scenario 'best provider' recommendations."""
    recommendations = [
        {
            "use_case": "通用型 AI Agent 钱包",
            "description": "需要灵活性和全场景覆盖",
            "recommended": "privy",
            "reason": "技术得分最高 + DeFi 全场景可达 + REST API 设计清晰",
        },
        {
            "use_case": "链上 DeFi (Swap + 借贷)",
            "description": "以 Base 链为主的 DeFi 场景",
            "recommended": "coinbase_agentkit",
            "reason": "Swap/Aave/Morpho 内置 action，Agent 声明即用（仅限 Base/ETH 主网）",
        },
        {
            "use_case": "衍生品交易 (Hyperliquid)",
            "description": "永续合约交易场景",
            "recommended": "privy",
            "alternates": ["coinbase_agentkit", "crossmint"],
            "reason": "REST signTypedData 支持 EIP-712，可签名 Hyperliquid approveAgent 授权，需 Agent 自行构造 typed data（~1-2d）",
        },
        {
            "use_case": "预测市场 (Polymarket)",
            "description": "预测市场交易场景",
            "recommended": "privy",
            "alternates": ["crossmint", "coinbase_agentkit"],
            "reason": "REST signTypedData 支持 EIP-712，可签名 CLOB 授权和订单 — 需自定义编码器但可行性最高",
        },
        {
            "use_case": "企业级风控",
            "description": "需要策略引擎和审计能力",
            "recommended": "privy",
            "reason": "唯一内置 Policy Engine 的供应商",
        },
    ]
    return recommendations


def main():
    defi_data = load_json(DEFI_MATRIX_PATH)
    if not defi_data:
        print(f"ERROR: {DEFI_MATRIX_PATH} not found", file=sys.stderr)
        sys.exit(1)

    tech_data = load_json(TECH_RESULTS_PATH)
    tech_scores = compute_tech_scores(tech_data)
    defi_scores = compute_defi_scores(defi_data)
    recommendations = build_use_case_recommendations(defi_scores, tech_scores)

    # Build combined provider list
    providers = []
    for p in defi_data["providers"]:
        pid = p["id"]
        tech = tech_scores.get(pid, {})
        defi = defi_scores.get(pid, {})
        providers.append({
            "id": pid,
            "name": p["name"],
            "architecture": p["architecture"],
            "technical": tech,
            "defi": defi,
        })

    output = {
        "meta": {
            "version": "v1.1",
            "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
            "sources": {
                "defi_matrix": str(DEFI_MATRIX_PATH.relative_to(REPO_ROOT)),
                "tech_results": str(TECH_RESULTS_PATH.relative_to(REPO_ROOT)) if tech_data else None,
            },
            "rating_note": "Ratings reflect AI Agent integration complexity, not human developer effort.",
        },
        "scenarios": defi_data["scenarios"],
        "weight_presets": {
            k: {"name": _PRESET_NAMES.get(k, k), **v}
            for k, v in defi_data["weight_presets"].items()
        },
        "rating_definitions": {
            k: {"label": v["label"], "emoji": v["emoji"], "proxy": v["numeric_proxy"]}
            for k, v in defi_data["rating_definitions"].items()
        },
        "providers": providers,
        "recommendations": recommendations,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Generated {OUTPUT_PATH.relative_to(REPO_ROOT)}")
    print(f"   {len(providers)} providers, {len(defi_data['scenarios'])} scenarios")


if __name__ == "__main__":
    main()
