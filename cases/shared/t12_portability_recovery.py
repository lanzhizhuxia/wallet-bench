"""t12 — Portability & recovery: wallet identity persistence and key export capability."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t12"
TEST_NAME = "portability_recovery"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("create_wallet", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的可移植性/恢复能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    checks: list[dict] = []

    # Phase 1: create wallet and record identity
    try:
        wallet1 = await adapter.create_wallet()
        addr1 = wallet1.address.strip().lower()
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            message=f"create_wallet 失败: {exc}",
        )

    checks.append({
        "test": "initial_create",
        "ok": bool(addr1),
        "msg": f"Created wallet: {addr1[:10]}...",
    })

    # Phase 2: teardown + re-setup — simulate session restart
    try:
        await adapter.teardown()
        await adapter.setup()
    except Exception as exc:
        checks.append({
            "test": "session_restart",
            "ok": False,
            "msg": f"Restart failed: {exc}",
        })
        elapsed = (time.perf_counter() - t0) * 1000
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="会话重启失败",
            detail={"checks": checks},
        )

    checks.append({
        "test": "session_restart",
        "ok": True,
        "msg": "Teardown + re-setup succeeded",
    })

    # Phase 3: create wallet again — check if identity persists or is new
    try:
        wallet2 = await adapter.create_wallet()
        addr2 = wallet2.address.strip().lower()
    except Exception as exc:
        checks.append({
            "test": "post_restart_create",
            "ok": False,
            "msg": f"Post-restart create failed: {exc}",
        })
        elapsed = (time.perf_counter() - t0) * 1000
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="重启后钱包创建失败",
            detail={"checks": checks},
        )

    # For local wallets (same key), address should be the same.
    # For custodial/TEE wallets, each create_wallet may return a new address.
    # Both behaviors are valid — we just document it.
    same_identity = addr1 == addr2
    checks.append({
        "test": "identity_persistence",
        "ok": True,  # both behaviors are valid
        "msg": f"{'Same address (deterministic)' if same_identity else 'New address (non-deterministic)'}: {addr2[:10]}...",
    })

    # Phase 4: sign after recovery (if supported)
    if adapter.capabilities().get("sign_message", False):
        try:
            sig = await adapter.sign_message("portability_test")
            checks.append({
                "test": "sign_after_recovery",
                "ok": bool(sig.signature),
                "msg": f"Sign after recovery: {'ok' if sig.signature else 'empty signature'}",
            })
        except Exception as exc:
            checks.append({
                "test": "sign_after_recovery",
                "ok": False,
                "msg": f"Sign after recovery failed: {exc}",
            })

    # Phase 5: check export capability (metadata only, don't actually export)
    caps = adapter.capabilities()
    has_export = caps.get("key_export", False)
    checks.append({
        "test": "export_capability",
        "ok": True,  # informational
        "msg": f"Key export: {'supported' if has_export else 'not supported'}",
    })

    elapsed = (time.perf_counter() - t0) * 1000
    all_ok = all(c["ok"] for c in checks)

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if all_ok else TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=f"Portability: {'确定性' if same_identity else '非确定性'} identity, {'所有检查通过' if all_ok else '存在失败'}",
        detail={"checks": checks, "same_identity": same_identity},
    )
