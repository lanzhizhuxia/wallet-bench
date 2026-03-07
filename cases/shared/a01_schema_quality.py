"""a01 — Schema quality for machine-readable adapter outputs."""
from __future__ import annotations

import time
from typing import Any

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "a01"
TEST_NAME = "schema_quality"

_VALID_TO = "0x0000000000000000000000000000000000000001"
_INVALID_TO = "0xinvalid"


def _has_error_info(meta: Any) -> bool:
    if not isinstance(meta, dict):
        return False
    for key in ("error", "message", "reason", "error_code", "code"):
        if str(meta.get(key, "")).strip():
            return True
    return False


def _is_tx_hash_like(tx_hash: str) -> bool:
    return bool(tx_hash) and tx_hash.startswith("0x") and len(tx_hash) >= 10


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    unsupported = adapter.provider_unsupported()

    if not caps.get("create_wallet", False) and not caps.get("send_transaction", False):
        owner = "provider" if {"create_wallet", "send_transaction"}.issubset(unsupported) else "benchmark"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="缺少核心能力（create_wallet/send_transaction），无法进行结构完整性验证。",
            detail={"capabilities": caps},
            owner=owner,
        )

    t0 = time.perf_counter()
    checks_passed = 0
    total_checks = 0
    notes: list[str] = []
    detail: dict[str, Any] = {"checks": [], "operations": {}}

    if caps.get("create_wallet", False):
        try:
            wallet = await adapter.create_wallet()
            detail["operations"]["create_wallet"] = {
                "address": wallet.address,
                "chain": wallet.chain,
                "meta": wallet.meta,
            }

            total_checks += 1
            ok_non_empty_address = bool(str(wallet.address).strip())
            if ok_non_empty_address:
                checks_passed += 1
            detail["checks"].append({"name": "wallet.address_non_empty", "ok": ok_non_empty_address})

            total_checks += 1
            ok_address_prefix = str(wallet.address).startswith("0x")
            if ok_address_prefix:
                checks_passed += 1
            detail["checks"].append({"name": "wallet.address_0x_prefix", "ok": ok_address_prefix})
        except Exception as exc:
            total_checks += 2
            notes.append(f"create_wallet 异常: {exc}")
            detail["operations"]["create_wallet_error"] = str(exc)
            detail["checks"].append({"name": "wallet.address_non_empty", "ok": False})
            detail["checks"].append({"name": "wallet.address_0x_prefix", "ok": False})
    else:
        notes.append("create_wallet 不支持，已跳过对应字段检查")

    if caps.get("sign_message", False):
        try:
            sign = await adapter.sign_message("schema-quality")
            detail["operations"]["sign_message"] = {
                "signature": sign.signature,
                "signer": sign.signer,
                "message_hash": sign.message_hash,
                "meta": sign.meta,
            }
            total_checks += 1
            ok_signature = bool(str(sign.signature).strip())
            if ok_signature:
                checks_passed += 1
            detail["checks"].append({"name": "sign.signature_non_empty", "ok": ok_signature})
        except Exception as exc:
            total_checks += 1
            notes.append(f"sign_message 异常: {exc}")
            detail["operations"]["sign_message_error"] = str(exc)
            detail["checks"].append({"name": "sign.signature_non_empty", "ok": False})
    else:
        notes.append("sign_message 不支持，按规格跳过签名字段检查")

    if caps.get("send_transaction", False):
        try:
            tx_ok = await adapter.send_transaction(TxParams(to=_VALID_TO, value=1))
            detail["operations"]["send_transaction_nominal"] = {
                "tx_hash": tx_ok.tx_hash,
                "status": tx_ok.status,
                "meta": tx_ok.meta,
            }
            total_checks += 1
            ok_nominal_schema = _is_tx_hash_like(tx_ok.tx_hash) or _has_error_info(tx_ok.meta)
            if ok_nominal_schema:
                checks_passed += 1
            detail["checks"].append({"name": "tx.nominal_hash_or_error_meta", "ok": ok_nominal_schema})
        except Exception as exc:
            total_checks += 1
            notes.append(f"send_transaction(正常路径) 异常: {exc}")
            detail["operations"]["send_transaction_nominal_error"] = str(exc)
            detail["checks"].append({"name": "tx.nominal_hash_or_error_meta", "ok": bool(str(exc).strip())})
            if str(exc).strip():
                checks_passed += 1

        try:
            tx_bad = await adapter.send_transaction(TxParams(to=_INVALID_TO, value=1))
            detail["operations"]["send_transaction_invalid"] = {
                "tx_hash": tx_bad.tx_hash,
                "status": tx_bad.status,
                "meta": tx_bad.meta,
            }
            total_checks += 1
            ok_invalid_schema = _is_tx_hash_like(tx_bad.tx_hash) or _has_error_info(tx_bad.meta)
            if ok_invalid_schema:
                checks_passed += 1
            detail["checks"].append({"name": "tx.invalid_hash_or_error_meta", "ok": ok_invalid_schema})
        except Exception as exc:
            total_checks += 1
            has_msg = bool(str(exc).strip())
            if has_msg:
                checks_passed += 1
            detail["operations"]["send_transaction_invalid_error"] = str(exc)
            detail["checks"].append({"name": "tx.invalid_hash_or_error_meta", "ok": has_msg})
            notes.append(f"send_transaction(非法地址路径) 异常: {exc}")
    else:
        notes.append("send_transaction 不支持，已跳过交易字段检查")

    elapsed = (time.perf_counter() - t0) * 1000
    score = (checks_passed / total_checks) if total_checks else 0.0
    status = TestStatus.PASS if total_checks > 0 and checks_passed == total_checks else TestStatus.FAIL

    message = f"schema checks: {checks_passed}/{total_checks} ({score:.2%})"
    if notes:
        message = f"{message}; {'; '.join(notes)}"

    detail["checks_passed"] = checks_passed
    detail["total_checks"] = total_checks
    detail["score"] = score

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=status,
        elapsed_ms=elapsed,
        message=message,
        detail=detail,
        owner="provider" if status == TestStatus.FAIL else "industry",
    )
