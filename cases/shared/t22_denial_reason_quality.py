"""t22 — Denial reason quality for rejected transactions."""
from __future__ import annotations

import time

from adapters.base import TestResult, TestStatus, TxParams, WalletAdapter

TEST_ID = "t22"
TEST_NAME = "denial_reason_quality"

_TO = "0x0000000000000000000000000000000000000000"
_HUGE_VALUE = 10**30


def _extract_error_fields(exc: Exception) -> tuple[str, str, str]:
    # 优先提取结构化字段（code/message/category）
    code = str(getattr(exc, "error_code", "") or getattr(exc, "code", "") or "").strip()
    category = str(getattr(exc, "category", "") or "").strip()
    message = str(exc).strip()

    if exc.args and isinstance(exc.args[0], dict):
        payload = exc.args[0]
        code = code or str(payload.get("error_code") or payload.get("code") or "").strip()
        category = category or str(payload.get("category") or "").strip()
        message = message or str(payload.get("message") or "").strip()

    return code, message, category


async def run(adapter: WalletAdapter, config: dict) -> TestResult:
    # 能力检查：需要交易提交能力来触发拒绝路径
    if not adapter.capabilities().get("send_transaction", False):
        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.INCONCLUSIVE,
            message="本轮基准未接入该供应商的拒绝原因质量评估前提能力，无法验证。不影响评分，计入结论置信度。",
            owner="benchmark",
        )

    t0 = time.perf_counter()
    try:
        tx = TxParams(to=_TO, value=_HUGE_VALUE)
        result = await adapter.send_transaction(tx)
        elapsed = (time.perf_counter() - t0) * 1000

        if result.tx_hash:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.FAIL,
                elapsed_ms=elapsed,
                message="预期应被拒绝，但交易成功返回 tx_hash",
                detail={"tx_hash": result.tx_hash, "meta": result.meta},
            )

        meta = result.meta if isinstance(result.meta, dict) else {}
        code = str(meta.get("error_code") or meta.get("code") or "").strip()
        msg = str(meta.get("message") or "").strip()
        category = str(meta.get("category") or "").strip()

        if code and msg:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=elapsed,
                message="拒绝原因结构化字段完整",
                detail={"error_code": code, "message": msg, "category": category, "meta": meta},
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="拒绝信息质量不足: 缺少 error_code 或 message",
            detail={"meta": meta},
        )
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        try:
            code, msg, category = _extract_error_fields(exc)
        except Exception as parse_exc:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.ERROR,
                elapsed_ms=elapsed,
                message=f"拒绝异常解析失败: {parse_exc}",
                detail={"raw_error": str(exc)},
            )

        if code and msg:
            return TestResult(
                test_id=TEST_ID,
                test_name=TEST_NAME,
                status=TestStatus.PASS,
                elapsed_ms=elapsed,
                message="拒绝异常包含结构化字段",
                detail={"error_code": code, "message": msg, "category": category},
            )

        return TestResult(
            test_id=TEST_ID,
            test_name=TEST_NAME,
            status=TestStatus.FAIL,
            elapsed_ms=elapsed,
            message="拒绝异常仅原始字符串，缺少结构化原因",
            detail={"raw_error": str(exc)},
        )
