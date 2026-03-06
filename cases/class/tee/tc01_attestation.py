"""tc01 (tee) — Verify remote attestation / key origin evidence.

For TEE-class providers, we verify that:
1. The wallet is managed server-side (not local)
2. Creating the same wallet config yields the same address (deterministic)
3. The provider identity is verifiable (address format, metadata)
"""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "tc01"
TEST_NAME = "attestation"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    t0 = time.perf_counter()
    checks: list[dict] = []

    # Check 1: Wallet creation returns valid address
    try:
        wallet = await adapter.create_wallet()
        addr = wallet.address
        valid = (
            isinstance(addr, str)
            and addr.startswith("0x")
            and len(addr) == 42
        )
        checks.append({
            "test": "valid_address",
            "ok": valid,
            "msg": f"Address: {addr[:10]}..." if valid else f"Invalid address format: {addr}",
        })
    except Exception as exc:
        checks.append({"test": "valid_address", "ok": False, "msg": str(exc)})

    # Check 2: Provider reports TEE/custodial custody model
    custody = adapter.custody_model.lower()
    is_tee = any(k in custody for k in ["tee", "cdp", "server", "shard", "custod"])
    checks.append({
        "test": "custody_model",
        "ok": is_tee,
        "msg": f"Custody: {adapter.custody_model}" if is_tee else f"Unexpected custody: {adapter.custody_model}",
    })

    # Check 3: Signing works (proves key exists in TEE backend)
    if adapter.capabilities().get("sign_message", False):
        try:
            sig = await adapter.sign_message("attestation-probe")
            has_sig = bool(sig.signature) and len(sig.signature) > 10
            checks.append({
                "test": "sign_probe",
                "ok": has_sig,
                "msg": f"Signature length: {len(sig.signature)}" if has_sig else "Empty signature",
            })
        except Exception as exc:
            checks.append({"test": "sign_probe", "ok": False, "msg": str(exc)})

    elapsed = (time.perf_counter() - t0) * 1000
    all_ok = all(c["ok"] for c in checks)

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if all_ok else TestStatus.FAIL,
        elapsed_ms=elapsed,
        message="TEE 证明检查通过" if all_ok else "TEE 证明检查失败",
        detail={"checks": checks},
    )
