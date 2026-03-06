"""Test case auto-discovery.

Scans ``cases/shared/*.py`` and ``cases/class/{arch_class}/*.py`` for modules
that expose ``TEST_ID``, ``TEST_NAME``, and an async ``run()`` function.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Coroutine

from adapters.base import TestResult, WalletAdapter

_CASES_ROOT = Path(__file__).resolve().parent


@dataclass
class TestSpec:
    test_id: str
    test_name: str
    run: Callable[[WalletAdapter, dict[str, Any]], Coroutine[Any, Any, TestResult]]
    source: str  # "shared" or "class/<name>"


def _load_module_specs(package_path: Path, package_name: str, source_label: str) -> list[TestSpec]:
    specs: list[TestSpec] = []
    if not package_path.is_dir():
        return specs

    for info in pkgutil.iter_modules([str(package_path)]):
        if info.name.startswith("_"):
            continue
        module_name = f"{package_name}.{info.name}"
        mod = importlib.import_module(module_name)
        test_id = getattr(mod, "TEST_ID", None)
        test_name = getattr(mod, "TEST_NAME", None)
        run_fn = getattr(mod, "run", None)
        if test_id and test_name and callable(run_fn):
            specs.append(TestSpec(
                test_id=test_id,
                test_name=test_name,
                run=run_fn,
                source=source_label,
            ))
    return specs


def discover(arch_class: str) -> list[TestSpec]:
    """Return all test specs for the given architecture class.

    Includes ``cases/shared/*`` (always) + ``cases/class/{arch_class}/*``
    (if the directory exists).
    """
    specs: list[TestSpec] = []

    # shared tests
    specs.extend(_load_module_specs(
        _CASES_ROOT / "shared",
        "cases.shared",
        "shared",
    ))

    # class-specific tests
    class_dir = _CASES_ROOT / "class" / arch_class
    if class_dir.is_dir():
        specs.extend(_load_module_specs(
            class_dir,
            f"cases.class.{arch_class}",
            f"class/{arch_class}",
        ))

    # Sort: shared first (by test_id), then class-specific (by test_id)
    specs.sort(key=lambda s: (0 if s.source == "shared" else 1, s.test_id))
    return specs
