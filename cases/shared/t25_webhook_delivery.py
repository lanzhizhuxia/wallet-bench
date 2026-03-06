"""t25 — Webhook delivery framework check."""
from __future__ import annotations

import inspect
import time
from typing import Any, Awaitable, cast

from adapters.base import TestResult, TestStatus, WalletAdapter

TEST_ID = "t25"
TEST_NAME = "webhook_delivery"


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    if not adapter.capabilities().get("webhook", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.SKIP,
            message="行业现状：目前所有评测供应商均未提供 Webhook 事件推送能力。作为市场成熟度观察指标保留。",
            owner="industry",
        )

    t0 = time.perf_counter()
    try:
        register_fn = getattr(adapter, "register_webhook", None)
        verify_fn = getattr(adapter, "verify_webhook", None)
        if not callable(register_fn) or not callable(verify_fn):
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.SKIP,
                elapsed_ms=(time.perf_counter() - t0) * 1000,
                message="行业现状：供应商声明支持 Webhook 但未暴露注册/验证接口，功能尚不完整。",
                owner="industry",
            )

        callback_url = str(config.get("webhook_callback_url", "https://example.invalid/wallet-bench-webhook"))
        event_name = str(config.get("webhook_event", "tx.confirmed"))

        register_call = register_fn(callback_url, event_name)
        if inspect.isawaitable(register_call):
            register_result = await cast(Awaitable[Any], register_call)
        else:
            register_result = register_call

        verify_call = verify_fn(callback_url, event_name)
        if inspect.isawaitable(verify_call):
            verify_result = await cast(Awaitable[Any], verify_call)
        else:
            verify_result = verify_call
        elapsed = (time.perf_counter() - t0) * 1000

        received = False
        if isinstance(verify_result, dict):
            received = bool(verify_result.get("received") or verify_result.get("delivered"))
        else:
            received = bool(getattr(verify_result, "received", False) or getattr(verify_result, "delivered", False))

        if not received:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message="webhook 已注册但未验证到事件送达",
                detail={"register_result": register_result, "verify_result": verify_result},
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.PASS,
            elapsed_ms=elapsed,
            message="webhook 注册并验证送达成功",
            detail={"register_result": register_result, "verify_result": verify_result},
        )
    except Exception as exc:
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.ERROR,
            elapsed_ms=(time.perf_counter() - t0) * 1000,
            message=str(exc),
        )
