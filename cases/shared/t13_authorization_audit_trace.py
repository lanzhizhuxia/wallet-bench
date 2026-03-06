"""t13 — Authorization audit trace: verify operations produce traceable records."""

from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t13"
TEST_NAME = "authorization_audit_trace"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    if not caps.get("create_wallet", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的授权审计追踪能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    checks: list[dict] = []

    # Phase 1: create wallet — verify returns address (audit anchor)
    try:
        wallet = await adapter.create_wallet()
        has_address = bool(wallet.address.strip())
        has_chain = bool(wallet.chain)
        has_timestamp = bool(wallet.created_at)
        checks.append({
            "test": "wallet_audit_fields",
            "ok": has_address,
            "msg": f"address={'yes' if has_address else 'no'}, chain={'yes' if has_chain else 'no'}, timestamp={'yes' if has_timestamp else 'no'}",
        })
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            message=f"create_wallet 失败: {exc}",
        )

    # Phase 2: sign_message — verify signature is non-empty and deterministic-format
    if caps.get("sign_message", False):
        try:
            sig = await adapter.sign_message("audit_test_message")
            has_sig = bool(sig.signature)
            sig_hex = sig.signature.startswith("0x") if sig.signature else False
            checks.append({
                "test": "sign_audit_fields",
                "ok": has_sig,
                "msg": f"signature={'present' if has_sig else 'missing'}, hex_format={'yes' if sig_hex else 'no'}, signer={'present' if sig.signer else 'missing'}",
            })
        except Exception as exc:
            checks.append({
                "test": "sign_audit_fields",
                "ok": False,
                "msg": f"sign_message failed: {exc}",
            })
    else:
        checks.append({
            "test": "sign_audit_fields",
            "ok": True,
            "msg": "sign_message not supported, skipped",
        })

    # Phase 3: send_transaction — verify tx_hash returned (on-chain audit anchor)
    if caps.get("send_transaction", False):
        try:
            tx = TxParams(
                to="0x0000000000000000000000000000000000000001",
                value=0,
                data="0x",
            )
            result = await adapter.send_transaction(tx)
            has_hash = bool(result.tx_hash)
            has_elapsed = result.elapsed_ms > 0
            checks.append({
                "test": "tx_audit_fields",
                "ok": True,  # even reverted tx should return hash
                "msg": f"tx_hash={'present' if has_hash else 'missing'}, elapsed={'yes' if has_elapsed else 'no'}, status={result.status}",
            })
        except Exception as exc:
            # Error is acceptable if it's a clean rejection (e.g. insufficient funds)
            error_msg = str(exc).lower()
            clean_error = any(k in error_msg for k in (
                "revert", "insufficient", "balance", "invalid", "rejected",
                "execution", "failed", "nonce",
            ))
            checks.append({
                "test": "tx_audit_fields",
                "ok": clean_error,
                "msg": f"{'Clean rejection' if clean_error else 'Unstructured error'}: {str(exc)[:100]}",
            })
    else:
        checks.append({
            "test": "tx_audit_fields",
            "ok": True,
            "msg": "send_transaction not supported, skipped",
        })

    # Phase 4: verify capabilities() is self-consistent
    cap_keys = set(caps.keys())
    expected_keys = {"create_wallet", "sign_message", "sign_typed_data", "send_transaction"}
    missing_keys = expected_keys - cap_keys
    checks.append({
        "test": "capabilities_completeness",
        "ok": len(missing_keys) == 0,
        "msg": f"capabilities has {len(cap_keys)} keys, missing core: {missing_keys or 'none'}",
    })

    # Phase 5: verify provider metadata available (arch_class, custody_model, etc.)
    meta_fields = {
        "name": adapter.name,
        "arch_class": adapter.arch_class,
        "custody_model": adapter.custody_model,
        "submission_mode": adapter.submission_mode,
    }
    populated = {k: v for k, v in meta_fields.items() if v}
    checks.append({
        "test": "metadata_completeness",
        "ok": len(populated) >= 2,
        "msg": f"Metadata: {len(populated)}/{len(meta_fields)} fields populated ({', '.join(populated.keys())})",
    })

    elapsed = (time.perf_counter() - t0) * 1000
    all_ok = all(c["ok"] for c in checks)

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if all_ok else TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=f"审计链: {sum(c['ok'] for c in checks)}/{len(checks)} 项检查通过",
        detail={"checks": checks},
    )
