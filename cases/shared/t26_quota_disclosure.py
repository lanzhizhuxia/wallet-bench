"""t26 — Quota disclosure and rate-limit metadata visibility."""
from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t26"
TEST_NAME = "quota_disclosure"


def _extract_quota_info(obj: object) -> dict:
    if isinstance(obj, dict):
        source = obj
    else:
        source = getattr(obj, "meta", {}) if hasattr(obj, "meta") else {}
        if not isinstance(source, dict):
            source = {}

    keys = (
        "rate_limit",
        "rate_limit_remaining",
        "rate_limit_reset",
        "quota",
        "quota_remaining",
        "retry_after",
        "x-ratelimit-limit",
        "x-ratelimit-remaining",
        "x-ratelimit-reset",
    )
    return {k: source.get(k) for k in keys if k in source}


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    caps = adapter.capabilities()
    if not caps.get("quota_headers", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.SKIP,
            message="行业现状：目前所有评测供应商均未提供配额/限额透明度数据。作为市场成熟度观察指标保留。",
            owner="industry",
        )

    t0 = time.perf_counter()
    try:
        if caps.get("sign_message", False):
            result = await adapter.sign_message("quota_disclosure_probe")
            action = "sign_message"
        elif caps.get("create_wallet", False):
            result = await adapter.create_wallet()
            action = "create_wallet"
        else:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.SKIP,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="行业现状：无法通过现有接口探测供应商的配额信息，功能尚不完整。",
                owner="industry",
            )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=str(exc),
        )

    elapsed = (time.perf_counter() - t0) * 1000
    quota_info = _extract_quota_info(result)
    if quota_info:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="检测到配额/限流元数据",
            detail={"action": action, "quota_info": quota_info},
        )

    return TestResult(
        test_id=TEST_ID,
        test_name=TEST_NAME,
        status=TestStatus.FAIL,
        elapsed_ms=elapsed,
        message="已声明 quota_headers 但响应中未发现配额信息",
        detail={"action": action},
    )
