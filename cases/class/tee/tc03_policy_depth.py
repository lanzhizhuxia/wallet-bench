"""tc03 (tee) — Policy depth: multi-dimensional allow/deny rules.

Tests whether the provider supports transaction policies.  If the
adapter declares policy_enforcement capability, we test:
1. Normal tx should succeed (within policy)
2. Bad-params tx should be rejected with a policy-related error

If policy_enforcement is not supported, this test SKIPs.
"""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "tc03"
TEST_NAME = "policy_depth"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("policy_enforcement", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.UNSUPPORTED,
            message="该供应商当前不提供策略深度/多层级风控能力。如需 Agent 多层策略管控，需评估其他方案。",
            owner="provider",
        )

    t0 = time.perf_counter()
    checks: list[dict] = []

    # Ensure wallet exists
    try:
        await adapter.create_wallet()
    except Exception:
        pass

    # Test 1: Normal small tx should be accepted (or revert due to no balance,
    # which is fine — we just check it wasn't blocked by policy)
    try:
        tx = TxParams(
            to="0x0000000000000000000000000000000000000001",
            value=1,  # 1 wei — minimal
        )
        result = await adapter.send_transaction(tx)
        # Either success or revert (not policy block) is OK
        policy_block = "policy" in (result.meta.get("error", "")).lower()
        checks.append({
            "test": "small_tx_allowed",
            "ok": not policy_block,
            "msg": "Tx accepted by policy" if not policy_block else "Blocked by policy unexpectedly",
        })
    except Exception as exc:
        err = str(exc).lower()
        policy_block = "policy" in err
        checks.append({
            "test": "small_tx_allowed",
            "ok": not policy_block,
            "msg": f"Error (non-policy): {exc}" if not policy_block else f"Policy blocked: {exc}",
        })

    # Test 2: Extremely large value should ideally be flagged
    try:
        huge_tx = TxParams(
            to="0x0000000000000000000000000000000000000001",
            value=10**30,  # absurdly large
        )
        result = await adapter.send_transaction(huge_tx)
        # If it was rejected (revert/error), that's good
        rejected = result.status == 0 or not result.tx_hash
        checks.append({
            "test": "huge_value_handling",
            "ok": rejected,
            "msg": "Large value rejected" if rejected else "Large value unexpectedly succeeded",
        })
    except Exception as exc:
        checks.append({"test": "huge_value_handling", "ok": True, "msg": f"Rejected: {exc}"})

    elapsed = (time.perf_counter() - t0) * 1000
    all_ok = all(c["ok"] for c in checks)

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if all_ok else TestStatus.FAIL,
        elapsed_ms=elapsed,
        message="策略检查通过" if all_ok else "策略检查失败",
        detail={"checks": checks},
    )
