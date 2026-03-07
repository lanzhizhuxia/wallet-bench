"""a02 — Machine-readable error handling quality."""
from __future__ import annotations

import re
import time
from typing import Any

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "a02"
TEST_NAME = "machine_errors"

_INVALID_TO = "0xinvalid"
_HUGE_VALUE = 10**30


def _extract_message_from_meta(meta: Any) -> str:
    if not isinstance(meta, dict):
        return ""
    for key in ("message", "error", "reason", "error_code", "code"):
        value = str(meta.get(key, "")).strip()
        if value:
            return value
    return ""


def _message_subject(msg: str) -> str:
    text = msg.strip().lower()
    text = re.sub(r"0x[0-9a-f]{6,}", "0x<hex>", text)
    text = re.sub(r"\d+", "<n>", text)
    if ":" in text:
        text = text.split(":", 1)[0].strip()
    if "\n" in text:
        text = text.splitlines()[0].strip()
    return text


async def _capture_sign_empty(adapter: WalletAdapter) -> tuple[bool, str, dict[str, Any]]:
    try:
        result = await adapter.sign_message("")
        msg = _extract_message_from_meta(result.meta)
        caught = bool(msg)
        return caught, msg, {"kind": "result", "signature": result.signature, "meta": result.meta}
    except Exception as exc:
        msg = str(exc).strip()
        return bool(msg), msg, {"kind": "exception", "error": msg}


async def _capture_send_invalid(adapter: WalletAdapter, value: int) -> tuple[bool, str, dict[str, Any]]:
    try:
        result = await adapter.send_transaction(TxParams(to=_INVALID_TO, value=value))
        msg = _extract_message_from_meta(result.meta)
        caught = bool(msg)
        return caught, msg, {"kind": "result", "tx_hash": result.tx_hash, "meta": result.meta}
    except Exception as exc:
        msg = str(exc).strip()
        return bool(msg), msg, {"kind": "exception", "error": msg}


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    unsupported = adapter.provider_unsupported()

    can_sign = caps.get("sign_message", False)
    can_send = caps.get("send_transaction", False)

    if not can_sign and not can_send:
        owner = "provider" if {"sign_message", "send_transaction"}.issubset(unsupported) else "benchmark"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="缺少 sign_message/send_transaction 能力，无法触发错误路径。",
            detail={"capabilities": caps},
            owner=owner,
        )

    if not can_send:
        owner = "provider" if "send_transaction" in unsupported else "benchmark"
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            elapsed_ms=0.0,
            message="缺少 send_transaction 能力，无法覆盖资源不存在错误类型。",
            detail={"capabilities": caps},
            owner=owner,
        )

    t0 = time.perf_counter()

    if can_sign:
        caught_a, msg_a, raw_a = await _capture_sign_empty(adapter)
        caught_c, msg_c, raw_c = await _capture_sign_empty(adapter)
        trigger = "sign_message_empty"
    else:
        caught_a, msg_a, raw_a = await _capture_send_invalid(adapter, 1)
        caught_c, msg_c, raw_c = await _capture_send_invalid(adapter, 1)
        trigger = "send_invalid_param"

    caught_b, msg_b, raw_b = await _capture_send_invalid(adapter, _HUGE_VALUE)

    non_empty_a = bool(msg_a)
    non_empty_b = bool(msg_b)
    non_empty_c = bool(msg_c)
    subject_a = _message_subject(msg_a)
    subject_c = _message_subject(msg_c)
    stable_same_class = bool(subject_a) and subject_a == subject_c

    checks = {
        "a_caught": caught_a,
        "a_message_non_empty": non_empty_a,
        "b_caught": caught_b,
        "b_message_non_empty": non_empty_b,
        "c_caught": caught_c,
        "c_message_non_empty": non_empty_c,
        "same_class_stable": stable_same_class,
    }

    passed = all(checks.values())
    elapsed = (time.perf_counter() - t0) * 1000

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.PASS if passed else TestStatus.FAIL,
        elapsed_ms=elapsed,
        message=(
            "错误可捕获、非空且稳定"
            if passed
            else "错误机读性不足：存在不可捕获/空信息/同类不稳定"
        ),
        detail={
            "trigger_for_a_and_c": trigger,
            "checks": checks,
            "messages": {"a": msg_a, "b": msg_b, "c": msg_c},
            "subjects": {"a": subject_a, "c": subject_c},
            "raw": {"a": raw_a, "b": raw_b, "c": raw_c},
        },
        owner="industry" if passed else "provider",
    )
