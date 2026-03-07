"""a03 — Deterministic response structure across repeated calls."""
from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "a03"
TEST_NAME = "deterministic_response"


def _field_presence(values: list[str]) -> bool:
    return all(bool(v.strip()) for v in values) or all(not v.strip() for v in values)


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    unsupported = adapter.provider_unsupported()
    t0 = time.perf_counter()

    if caps.get("create_wallet", False):
        try:
            first_wallet = await adapter.create_wallet()
        except Exception as exc:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.ERROR,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message=f"create_wallet 预检查失败: {exc}",
                detail={"error": str(exc)},
                owner="provider",
            )
    else:
        first_wallet = None

    if caps.get("sign_message", False):
        message = "determinism-test"
        results = []
        for _ in range(3):
            try:
                sign = await adapter.sign_message(message)
            except Exception as exc:
                return TestResult(
                    test_id=TEST_ID,
                    test_name=TEST_NAME,
                    status=TestStatus.FAIL,
                    elapsed_ms=(time.perf_counter() - t0) * 1000,
                    message=f"sign_message 重复调用出现不可稳定异常: {exc}",
                    detail={"error": str(exc)},
                    owner="provider",
                )
            results.append(sign)

        sig_lengths = [len(r.signature or "") for r in results]
        signers = [str(r.signer or "") for r in results]
        sig_non_empty = [bool((r.signature or "").strip()) for r in results]

        checks = {
            "signature_non_empty_all": all(sig_non_empty),
            "signature_length_consistent": len(set(sig_lengths)) == 1,
            "signer_presence_consistent": _field_presence(signers),
            "signer_value_consistent_if_present": len({s for s in signers if s.strip()}) <= 1,
        }
        passed = all(checks.values())

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS if passed else TestStatus.FAIL,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=(
                "重复签名返回结构一致"
                if passed
                else "重复签名返回结构不一致（非值比较）"
            ),
            detail={
                "mode": "sign_message",
                "checks": checks,
                "signature_lengths": sig_lengths,
                "signer_values": signers,
                "create_wallet_preview": {
                    "address": getattr(first_wallet, "address", ""),
                    "chain": getattr(first_wallet, "chain", ""),
                },
            },
            owner="industry" if passed else "provider",
        )

    if not caps.get("create_wallet", False):
        owner = "provider" if {"create_wallet", "sign_message"}.issubset(unsupported) else "benchmark"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message="sign_message 与 create_wallet 均不可用，无法执行结构一致性测试。",
            detail={"capabilities": caps},
            owner=owner,
        )

    wallets = [first_wallet]
    for _ in range(2):
        try:
            wallets.append(await adapter.create_wallet())
        except Exception as exc:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message=f"create_wallet 重复调用异常: {exc}",
                detail={"error": str(exc)},
                owner="provider",
            )

    addresses = [str((w.address if w else "") or "") for w in wallets]
    chains = [str((w.chain if w else "") or "") for w in wallets]
    metas = [w.meta if w else {} for w in wallets]

    checks = {
        "address_non_empty_all": all(a.strip() for a in addresses),
        "address_prefix_consistent": all(a.startswith("0x") for a in addresses),
        "chain_presence_consistent": _field_presence(chains),
        "meta_type_consistent": all(isinstance(m, dict) for m in metas),
    }
    passed = all(checks.values())

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if passed else TestStatus.FAIL,
        elapsed_ms=(time.perf_counter() - t0) * 1000,
        message=(
            "sign_message 不可用，create_wallet 三次结构一致"
            if passed
            else "create_wallet 三次返回结构不一致"
        ),
        detail={
            "mode": "create_wallet_fallback",
            "checks": checks,
            "addresses": addresses,
            "chains": chains,
        },
        owner="industry" if passed else "provider",
    )
