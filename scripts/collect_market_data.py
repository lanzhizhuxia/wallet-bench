#!/usr/bin/env python3
"""Collect market activity proxy metrics for WaaS competitors.

Fetches data from 6 public sources and writes JSON files for the dashboard:
  - npm weekly downloads      → web/data/market_npm.json
  - PyPI weekly downloads     → web/data/market_pypi.json
  - GitHub activity           → web/data/market_github.json
  - Status Page incidents     → web/data/market_status.json
  - Docs / changelog density  → web/data/market_docs.json
  - On-chain wallet activity  → web/data/market_onchain.json

Usage:
  python3 scripts/collect_market_data.py

Environment variables:
  GITHUB_TOKEN  — GitHub personal access token (optional locally, provided
                  automatically in GitHub Actions).  Without it GitHub API
                  requests are limited to 60/hour.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import time
import urllib.parse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "web" / "data"

OUTPUT_NPM = DATA_DIR / "market_npm.json"
OUTPUT_PYPI = DATA_DIR / "market_pypi.json"
OUTPUT_GITHUB = DATA_DIR / "market_github.json"
OUTPUT_STATUS = DATA_DIR / "market_status.json"
OUTPUT_DOCS = DATA_DIR / "market_docs.json"
OUTPUT_ONCHAIN = DATA_DIR / "market_onchain.json"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCHEMA_VERSION = "1.0"
REQUEST_TIMEOUT = 10  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 1  # seconds (doubles each retry)

# ---------------------------------------------------------------------------
# Provider → package / repo / status page mappings
# ---------------------------------------------------------------------------
NPM_PACKAGES: dict[str, list[str]] = {
    "privy": [
        "@privy-io/server-auth",
        "@privy-io/react-auth",
        "@privy-io/node",
    ],
    "coinbase": [
        "@coinbase/agentkit",
        "@coinbase/coinbase-sdk",
    ],
    "crossmint": [
        "@crossmint/wallets-sdk",
        "@crossmint/client-sdk-smart-wallet",
    ],
    "bnbchain_mcp": [
        "@bnb-chain/mcp",
    ],
    "moonpay": [
        "@moonpay/cli",
    ],
    "minara": [
        "minara",
    ],
}

PYPI_PACKAGES: dict[str, list[str]] = {
    "coinbase": ["coinbase-agentkit"],
}

GITHUB_REPOS: dict[str, list[str]] = {
    "privy": ["privy-io/privy-mcp-server"],
    "coinbase": ["coinbase/agentkit", "coinbase/cdp-sdk-python"],
    "crossmint": ["Crossmint/crossmint-sdk", "Crossmint/mcp-crossmint-checkout"],
    "bnbchain_mcp": ["bnb-chain/bnbchain-mcp"],
    "moonpay": [],  # no public repos
    "minara": ["Minara-AI/skills"],
}

# Status page base URLs (None = no known status page)
STATUS_PAGES: dict[str, str | None] = {
    "privy": "https://privy.statuspage.io",
    "coinbase": "https://coinbase.statuspage.io",
    "crossmint": "https://status.crossmint.com",
    "bnbchain_mcp": None,
    "moonpay": None,
    "minara": None,
}

# Per-repo docs/changelog paths (empty list = no tracked paths)
DOCS_PATHS_BY_REPO: dict[str, list[str]] = {
    "privy-io/privy-mcp-server":        [],
    "coinbase/agentkit":                ["python/coinbase-agentkit/CHANGELOG.md",
                                         "python/coinbase-agentkit/changelog.d"],
    "coinbase/cdp-sdk-python":          [],
    "Crossmint/crossmint-sdk":          [".changeset",
                                         "packages/common/CHANGELOG.md",
                                         "packages/wallets/CHANGELOG.md"],
    "Crossmint/mcp-crossmint-checkout": [],
    "bnb-chain/bnbchain-mcp":           [],
    "Minara-AI/skills":                 ["skills/minara/SKILL.md"],
}

BREAKING_KEYWORDS: list[str] = ["breaking", "BREAKING", "breaking change"]

# ERC-4337 factory labels（BundleBear PROVIDER 字段 "factory - xxx" 的 xxx 部分）
BUNDLEBEAR_4337_LABELS: dict[str, str] = {
    "coinbase_smart_wallet": "coinbase",
}

# EIP-7702 authorized contract labels（BundleBear PROVIDER 字段 "eip7702 - xxx" 的 xxx 部分）
BUNDLEBEAR_7702_LABELS: dict[str, str] = {
    "Coinbase Wallet": "coinbase",
}

# Crossmint: 通过 ZeroDev Kernel 工厂追踪（上界估计，含同工厂的其他 Kernel 客户）
BUNDLEBEAR_CROSSMINT_FACTORY_LABEL = "zerodev_kernel"
CROSSMINT_PROVIDER_ID = "crossmint"

# 不可追踪供应商的原因说明
ONCHAIN_NOT_TRACKABLE: dict[str, str] = {
    "privy":       "不部署自有工厂合约，复用底层实现（Coinbase/Kernel/Safe等），链上无法区分来源",
    "bnbchain_mcp": "本地 EOA 钱包，无工厂合约",
    "moonpay":     "HD 钱包架构，链上无工厂合约",
    "minara":      "托管钱包，链上不可追踪",
}

# ---------------------------------------------------------------------------
# Structured logging (JSON lines)
# ---------------------------------------------------------------------------

class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "level": record.levelname,
            "msg": record.getMessage(),
        }
        if hasattr(record, "extra"):
            entry.update(record.extra)  # type: ignore[arg-type]
        return json.dumps(entry, ensure_ascii=False)


log = logging.getLogger("collect_market_data")
_handler = logging.StreamHandler(sys.stderr)
_handler.setFormatter(_JsonFormatter())
log.addHandler(_handler)
log.setLevel(logging.INFO)


def _log(level: int, msg: str, **extra: object) -> None:
    record = log.makeRecord(
        log.name, level, "(collect)", 0, msg, (), None,
    )
    record.extra = extra  # type: ignore[attr-defined]
    log.handle(record)


def log_info(msg: str, **kw: object) -> None:
    _log(logging.INFO, msg, **kw)


def log_warn(msg: str, **kw: object) -> None:
    _log(logging.WARNING, msg, **kw)


def log_error(msg: str, **kw: object) -> None:
    _log(logging.ERROR, msg, **kw)


# ---------------------------------------------------------------------------
# HTTP helper with retry
# ---------------------------------------------------------------------------

def _get(url: str, headers: dict[str, str] | None = None) -> requests.Response:
    """GET with retries and exponential backoff.

    Only retries on transient errors (5xx, timeouts, connection errors).
    Client errors (4xx) are raised immediately — retrying won't help.
    """
    backoff = RETRY_BACKOFF
    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.HTTPError as exc:
            # 4xx → not transient, raise immediately
            status_code = exc.response.status_code if exc.response is not None else 0
            if 0 < status_code < 500:
                raise
            last_exc = exc
            log_warn(
                f"HTTP GET failed (attempt {attempt}/{MAX_RETRIES})",
                url=url, error=str(exc),
            )
            if attempt < MAX_RETRIES:
                time.sleep(backoff)
                backoff *= 2
        except requests.RequestException as exc:
            last_exc = exc
            log_warn(
                f"HTTP GET failed (attempt {attempt}/{MAX_RETRIES})",
                url=url, error=str(exc),
            )
            if attempt < MAX_RETRIES:
                time.sleep(backoff)
                backoff *= 2
    raise last_exc  # type: ignore[misc]


def _github_headers() -> dict[str, str]:
    token = os.environ.get("GITHUB_TOKEN", "")
    h: dict[str, str] = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


# ---------------------------------------------------------------------------
# 1. npm weekly downloads
# ---------------------------------------------------------------------------

def _fetch_npm_downloads(package: str) -> int | None:
    """Fetch last-week download count for a single npm package."""
    encoded = urllib.parse.quote(package, safe="")
    url = f"https://api.npmjs.org/downloads/point/last-week/{encoded}"
    try:
        data = _get(url).json()
        downloads = data.get("downloads")
        if downloads is not None:
            log_info("npm ok", package=package, downloads=downloads)
            return int(downloads)
        log_warn("npm missing downloads field", package=package, data=data)
        return None
    except Exception as exc:
        log_error("npm fetch failed", package=package, error=str(exc))
        return None


def collect_npm() -> dict:
    """Collect npm downloads for all providers. Returns output dict."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    providers: dict[str, dict] = {}

    for provider, packages in NPM_PACKAGES.items():
        pkg_results: list[dict] = []
        total: int = 0
        all_ok = True

        for pkg in packages:
            dl = _fetch_npm_downloads(pkg)
            if dl is not None:
                pkg_results.append({"package": pkg, "weekly_downloads": dl})
                total += dl
            else:
                pkg_results.append({
                    "package": pkg,
                    "weekly_downloads": None,
                    "error": "fetch failed",
                })
                all_ok = False

        providers[provider] = {
            "packages": pkg_results,
            "total_weekly_downloads": total if all_ok else None,
            "partial": not all_ok,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "source": "npm",
        "collected_at": now,
        "period": "last-week",
        "providers": providers,
    }


# ---------------------------------------------------------------------------
# 2. PyPI weekly downloads
# ---------------------------------------------------------------------------

def _fetch_pypi_downloads(package: str) -> int | None:
    """Fetch last-week download count for a single PyPI package."""
    url = f"https://pypistats.org/api/packages/{package}/recent?period=week"
    try:
        data = _get(url).json()
        downloads = data.get("data", {}).get("last_week")
        if downloads is not None:
            log_info("pypi ok", package=package, downloads=downloads)
            return int(downloads)
        log_warn("pypi missing downloads field", package=package, data=data)
        return None
    except Exception as exc:
        log_error("pypi fetch failed", package=package, error=str(exc))
        return None


def collect_pypi() -> dict:
    """Collect PyPI downloads for all providers. Returns output dict."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    providers: dict[str, dict] = {}

    for provider, packages in PYPI_PACKAGES.items():
        pkg_results: list[dict] = []
        total: int = 0
        all_ok = True

        for pkg in packages:
            dl = _fetch_pypi_downloads(pkg)
            if dl is not None:
                pkg_results.append({"package": pkg, "weekly_downloads": dl})
                total += dl
            else:
                pkg_results.append({
                    "package": pkg,
                    "weekly_downloads": None,
                    "error": "fetch failed",
                })
                all_ok = False

        providers[provider] = {
            "packages": pkg_results,
            "total_weekly_downloads": total if all_ok else None,
            "partial": not all_ok,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "source": "pypi",
        "collected_at": now,
        "period": "last-week",
        "providers": providers,
    }


# ---------------------------------------------------------------------------
# 3. GitHub activity
# ---------------------------------------------------------------------------

def _count_github_issues_created(
    owner_repo: str,
    since_iso: str,
    headers: dict[str, str],
) -> int:
    """Count issues (excluding PRs) created in the last 30d via Search API."""
    since_date = since_iso[:10]  # YYYY-MM-DD
    q = f"repo:{owner_repo} is:issue created:>={since_date}"
    url = f"https://api.github.com/search/issues?q={urllib.parse.quote(q)}&per_page=1"
    try:
        resp = _get(url, headers=headers)
        return resp.json().get("total_count", 0)
    except Exception as exc:
        log_warn("github issues search failed", repo=owner_repo, error=str(exc))
        return 0


def _fetch_github_repo(owner_repo: str, headers: dict[str, str]) -> dict | None:
    """Fetch stars, recent commits, recent issues, and last push for a repo."""
    try:
        # Basic repo info (stars, pushed_at)
        repo_url = f"https://api.github.com/repos/{owner_repo}"
        repo_data = _get(repo_url, headers=headers).json()
        stars = repo_data.get("stargazers_count", 0)
        pushed_at = repo_data.get("pushed_at")

        # Commits in last 30 days
        since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        commits_30d = _count_github_items(
            owner_repo, "commits", f"since={since}", headers,
        )

        # Issues created in last 30 days (excludes PRs)
        issues_30d = _count_github_issues_created(
            owner_repo, since, headers,
        )

        result = {
            "repo": owner_repo,
            "stars": stars,
            "commits_30d": commits_30d,
            "open_issues_created_30d": issues_30d,
            "last_push": pushed_at,
        }
        log_info("github repo ok", **result)
        return result

    except Exception as exc:
        log_error("github repo failed", repo=owner_repo, error=str(exc))
        return None


def _count_github_items(
    owner_repo: str,
    endpoint: str,
    query: str,
    headers: dict[str, str],
) -> int:
    """Count items via pagination (per_page=1, read last page from Link)."""
    url = (
        f"https://api.github.com/repos/{owner_repo}/{endpoint}"
        f"?{query}&per_page=1"
    )
    resp = _get(url, headers=headers)
    link = resp.headers.get("Link", "")
    if 'rel="last"' in link:
        # Parse last page number from Link header
        for part in link.split(","):
            if 'rel="last"' in part:
                # Extract page=N
                m = re.search(r"[&?]page=(\d+)", part)
                if m:
                    return int(m.group(1))
    # Fallback: if only one page, count items in response
    data = resp.json()
    return len(data) if isinstance(data, list) else 0


def collect_github() -> dict:
    """Collect GitHub activity for all providers."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    headers = _github_headers()
    providers: dict[str, dict] = {}

    for provider, repos in GITHUB_REPOS.items():
        if not repos:
            providers[provider] = {
                "repos": [],
                "total_stars": None,
                "total_commits_30d": None,
                "total_open_issues_created_30d": None,
                "latest_push": None,
                "partial": False,
                "note": "no public repos to track",
            }
            log_info("github skipped", provider=provider, reason="no public repos")
            continue

        repo_results: list[dict] = []
        all_ok = True

        for repo in repos:
            result = _fetch_github_repo(repo, headers)
            if result is not None:
                repo_results.append(result)
            else:
                repo_results.append({
                    "repo": repo,
                    "stars": None,
                    "commits_30d": None,
                    "open_issues_created_30d": None,
                    "last_push": None,
                    "error": "fetch failed",
                })
                all_ok = False

        # Aggregate: sum commits/issues, max stars, latest push
        total_stars = sum(r["stars"] for r in repo_results if r.get("stars") is not None)
        total_commits = sum(r["commits_30d"] for r in repo_results if r.get("commits_30d") is not None)
        total_issues = sum(r["open_issues_created_30d"] for r in repo_results if r.get("open_issues_created_30d") is not None)
        pushes = [r["last_push"] for r in repo_results if r.get("last_push")]
        latest_push = max(pushes) if pushes else None

        providers[provider] = {
            "repos": repo_results,
            "total_stars": total_stars if all_ok else None,
            "total_commits_30d": total_commits if all_ok else None,
            "total_open_issues_created_30d": total_issues if all_ok else None,
            "latest_push": latest_push,
            "partial": not all_ok,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "source": "github",
        "collected_at": now,
        "providers": providers,
    }


# ---------------------------------------------------------------------------
# 4. Status Page (Statuspage.io)
# ---------------------------------------------------------------------------

def _fetch_status_incidents(base_url: str) -> dict | None:
    """Fetch incidents from a Statuspage.io-compatible API and compute 30d stats."""
    url = f"{base_url}/api/v2/incidents.json"
    try:
        resp = _get(url)
        content_type = resp.headers.get("Content-Type", "")
        if "json" not in content_type:
            log_error(
                "status page returned non-JSON",
                url=url, content_type=content_type,
            )
            return None

        data = resp.json()
        incidents = data.get("incidents", [])
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)

        count_30d = 0
        resolution_minutes: list[float] = []

        for inc in incidents:
            created = inc.get("created_at", "")
            if not created:
                continue
            try:
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            except ValueError:
                continue

            if created_dt < cutoff:
                break

            count_30d += 1

            resolved = inc.get("resolved_at")
            if resolved:
                try:
                    resolved_dt = datetime.fromisoformat(resolved.replace("Z", "+00:00"))
                    delta = (resolved_dt - created_dt).total_seconds() / 60.0
                    if delta >= 0:
                        resolution_minutes.append(delta)
                except ValueError:
                    pass

        mttr = (
            round(sum(resolution_minutes) / len(resolution_minutes), 1)
            if resolution_minutes
            else None
        )

        result = {
            "incidents_30d": count_30d,
            "mttr_minutes": mttr,
            "resolved_count": len(resolution_minutes),
        }
        log_info("status page ok", url=base_url, **result)
        return result

    except Exception as exc:
        log_error("status page failed", url=base_url, error=str(exc))
        return None


def _fetch_squadcast_incidents(base_url: str) -> dict | None:
    """Fetch incidents from a Squadcast-powered status page (__NEXT_DATA__)."""
    try:
        resp = _get(base_url)
        html = resp.text
        match = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            html,
        )
        if not match:
            log_error("squadcast: no __NEXT_DATA__", url=base_url)
            return None

        data = json.loads(match.group(1))
        props = data.get("props", {}).get("pageProps", {})
        history = props.get("history", [])
        ongoing = props.get("onGoingIssues", {}).get("issues", [])

        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        count_30d = 0
        resolution_minutes: list[float] = []

        for day in history:
            for issue in day.get("issues", []):
                created = issue.get("begins_at") or issue.get("created_at", "")
                if not created:
                    continue
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    continue
                if created_dt < cutoff:
                    continue
                count_30d += 1
                resolved = issue.get("resolved_at") or issue.get("ends_at")
                if resolved:
                    try:
                        resolved_dt = datetime.fromisoformat(resolved.replace("Z", "+00:00"))
                        delta = (resolved_dt - created_dt).total_seconds() / 60.0
                        if delta >= 0:
                            resolution_minutes.append(delta)
                    except ValueError:
                        pass

        count_30d += len(ongoing)

        mttr = (
            round(sum(resolution_minutes) / len(resolution_minutes), 1)
            if resolution_minutes
            else None
        )

        result = {
            "incidents_30d": count_30d,
            "mttr_minutes": mttr,
            "resolved_count": len(resolution_minutes),
        }
        log_info("squadcast status ok", url=base_url, **result)
        return result

    except Exception as exc:
        log_error("squadcast status failed", url=base_url, error=str(exc))
        return None


def collect_status() -> dict:
    """Collect Status Page data for all providers."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    providers: dict[str, dict] = {}

    for provider, base_url in STATUS_PAGES.items():
        if base_url is None:
            providers[provider] = {
                "incidents_30d": None,
                "mttr_minutes": None,
                "status_page_url": None,
                "note": "no known public status page",
            }
            log_info("status page skipped", provider=provider, reason="no known page")
            continue

        result = _fetch_status_incidents(base_url)
        if result is None:
            # Statuspage.io API 不可用，尝试 Squadcast 解析
            result = _fetch_squadcast_incidents(base_url)
        if result is not None:
            providers[provider] = {
                **result,
                "status_page_url": base_url,
            }
        else:
            providers[provider] = {
                "incidents_30d": None,
                "mttr_minutes": None,
                "status_page_url": base_url,
                "error": "fetch failed",
            }

    return {
        "schema_version": SCHEMA_VERSION,
        "source": "statuspage",
        "collected_at": now,
        "period": "last-30d",
        "providers": providers,
    }


# ---------------------------------------------------------------------------
# 5. Docs / changelog density
# ---------------------------------------------------------------------------

def _fetch_docs_activity(
    owner_repo: str,
    headers: dict[str, str],
) -> dict | None:
    """Fetch docs/changelog commit count (30d) and breaking change signals."""
    doc_paths = DOCS_PATHS_BY_REPO.get(owner_repo, [])
    if not doc_paths:
        result = {
            "repo": owner_repo,
            "doc_commits_30d": 0,
            "breaking_change_commits_30d": 0,
            "paths_checked": [],
            "note": "no tracked docs paths",
        }
        log_info("docs activity skipped", repo=owner_repo, reason="no tracked paths")
        return result

    since = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    total_doc_commits = 0
    breaking_commits = 0
    paths_checked: list[str] = []

    for doc_path in doc_paths:
        url = (
            f"https://api.github.com/repos/{owner_repo}/commits"
            f"?path={urllib.parse.quote(doc_path)}&since={since}&per_page=100"
        )
        try:
            resp = _get(url, headers=headers)
            commits = resp.json()
            if not isinstance(commits, list):
                continue

            paths_checked.append(doc_path)
            total_doc_commits += len(commits)

            for c in commits:
                msg = (c.get("commit", {}).get("message", "")).lower()
                if any(kw.lower() in msg for kw in BREAKING_KEYWORDS):
                    breaking_commits += 1

        except requests.HTTPError as exc:
            if exc.response is not None and exc.response.status_code == 404:
                log_error("docs repo not found", repo=owner_repo, error=str(exc))
                return None
            continue
        except Exception:
            continue

    result = {
        "repo": owner_repo,
        "doc_commits_30d": total_doc_commits,
        "breaking_change_commits_30d": breaking_commits,
        "paths_checked": paths_checked,
    }
    log_info("docs activity ok", **result)
    return result


def collect_docs() -> dict:
    """Collect docs/changelog density for all providers."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    headers = _github_headers()
    providers: dict[str, dict] = {}

    for provider, repos in GITHUB_REPOS.items():
        if not repos:
            providers[provider] = {
                "repos": [],
                "total_doc_commits_30d": None,
                "total_breaking_change_commits_30d": None,
                "breaking_change_ratio": None,
                "partial": False,
                "note": "no public repos to track",
            }
            log_info("docs skipped", provider=provider, reason="no public repos")
            continue

        repo_results: list[dict] = []
        total_doc_commits = 0
        total_breaking = 0
        all_ok = True

        for repo in repos:
            result = _fetch_docs_activity(repo, headers)
            if result is not None:
                repo_results.append(result)
                total_doc_commits += result["doc_commits_30d"]
                total_breaking += result["breaking_change_commits_30d"]
            else:
                repo_results.append({
                    "repo": repo,
                    "doc_commits_30d": None,
                    "breaking_change_commits_30d": None,
                    "error": "fetch failed",
                })
                all_ok = False

        breaking_ratio = (
            round(total_breaking / total_doc_commits, 3)
            if total_doc_commits > 0
            else 0.0
        )

        providers[provider] = {
            "repos": repo_results,
            "total_doc_commits_30d": total_doc_commits if all_ok else None,
            "total_breaking_change_commits_30d": total_breaking if all_ok else None,
            "breaking_change_ratio": breaking_ratio if all_ok else None,
            "partial": not all_ok,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "source": "github-docs",
        "collected_at": now,
        "period": "last-30d",
        "providers": providers,
    }


# ---------------------------------------------------------------------------
# 6. On-chain active wallets (BundleBear)
# ---------------------------------------------------------------------------


def _read_existing_snapshot(path: Path) -> dict | None:
    """Read existing JSON snapshot for stale fallback."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        log_warn("failed to read existing snapshot", path=str(path), error=str(exc))
    return None


def collect_onchain() -> dict:
    """Collect on-chain active wallet counts via BundleBear activation API.

    Tracks two dimensions per provider:
      - ERC-4337: Smart Wallet factory activations ("factory - xxx")
      - EIP-7702: EOA delegation authorizations ("eip7702 - xxx")

    Coinbase has both dimensions (factory + 7702 impl).
    Crossmint tracked as upper-bound via ZeroDev Kernel factory.
    Other providers marked not_trackable with reasons.

    On failure, falls back to the last successful snapshot marked as stale.
    """
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    providers: dict = {}
    latest_month: str | None = None
    fetch_ok = False

    # 1. 采集 BundleBear erc4337-activation 数据（包含 ERC-4337 + EIP-7702 双维度，无需认证）
    url = "https://bundlebear-api.onrender.com/erc4337-activation?chain=all&timeframe=month"
    erc4337_data: dict[str, int] = {}   # BundleBear label -> count
    eip7702_data: dict[str, int] = {}   # BundleBear label -> count
    try:
        resp = _get(url)
        data = resp.json()
        rows = data.get("new_users_provider_chart", [])
        # 取最近一个完整月的数据
        # BundleBear 的当月数据可能不完整，优先使用上一个完整月
        all_months: set[str] = set()
        for row in rows:
            date = row.get("DATE", "")
            if date:
                all_months.add(date)
        sorted_months = sorted(all_months, reverse=True)
        # 当前月（可能不完整）用第二新的月份；若只有一个月则用它
        latest_month = sorted_months[1] if len(sorted_months) > 1 else (sorted_months[0] if sorted_months else None)
        for row in rows:
            if row.get("DATE") != latest_month:
                continue
            provider_raw = row.get("PROVIDER", "")
            count = row.get("NUM_ACCOUNTS")
            if not provider_raw or count is None:
                continue
            count = int(count)
            # 分离两个维度的数据
            if provider_raw.startswith("factory - "):
                label = provider_raw[len("factory - "):]
                erc4337_data[label] = erc4337_data.get(label, 0) + count
            elif provider_raw.startswith("eip7702 - "):
                label = provider_raw[len("eip7702 - "):]
                eip7702_data[label] = eip7702_data.get(label, 0) + count
            # Safe4337Module / Other / unknown 等忽略（不归属特定供应商）
        log_info("bundlebear fetch ok", rows=len(rows), latest_month=latest_month,
                 erc4337_labels=len(erc4337_data), eip7702_labels=len(eip7702_data))
        fetch_ok = True
    except Exception as exc:
        log_error("bundlebear fetch failed", error=str(exc))
        fetch_ok = False

    # 2. 如果 BundleBear 失败，尝试读取上次成功的快照
    if not fetch_ok:
        existing = _read_existing_snapshot(OUTPUT_ONCHAIN)
        if existing:
            existing["stale"] = True
            existing["stale_since"] = existing.get("stale_since") or now
            existing.setdefault("data_freshness", {})
            existing["data_freshness"]["collection_status"] = "stale"
            existing["collected_at"] = now
            log_warn("using stale onchain snapshot", stale_since=existing["stale_since"])
            return existing
        log_error("no historical snapshot available, returning empty onchain data")

    # 3. 可追踪供应商：Coinbase（ERC-4337 + EIP-7702 双维度）
    for label_4337, provider_id in BUNDLEBEAR_4337_LABELS.items():
        label_7702 = None
        for k, v in BUNDLEBEAR_7702_LABELS.items():
            if v == provider_id:
                label_7702 = k
                break
        if not fetch_ok:
            providers[provider_id] = {
                "trackable": True,
                "erc4337_active_wallets_30d": None,
                "eip7702_live_accounts": None,
                "total_onchain_footprint": None,
                "error": "BundleBear API fetch failed",
                "source": "bundlebear",
            }
        else:
            c4337 = erc4337_data.get(label_4337)
            c7702 = eip7702_data.get(label_7702) if label_7702 else None
            total = (c4337 or 0) + (c7702 or 0) if (c4337 is not None or c7702 is not None) else None
            providers[provider_id] = {
                "trackable": True,
                "erc4337_active_wallets_30d": c4337,
                "eip7702_live_accounts": c7702,
                "total_onchain_footprint": total,
                "source": "bundlebear",
                "bundlebear_labels": {
                    "erc4337": label_4337,
                    **({"eip7702": label_7702} if label_7702 else {}),
                },
                "note": "ERC-4337 + EIP-7702 双维度。4337=月度新激活智能钱包，7702=月度新授权 EOA。两者不重叠。",
            }
            log_info("onchain data", provider=provider_id,
                     erc4337=c4337, eip7702=c7702, total=total)

    # 4. Crossmint（partial tracking，上界估计）
    if fetch_ok:
        crossmint_count = erc4337_data.get(BUNDLEBEAR_CROSSMINT_FACTORY_LABEL)
        providers[CROSSMINT_PROVIDER_ID] = {
            "trackable": "partial",
            "erc4337_active_wallets_30d": crossmint_count,
            "eip7702_live_accounts": None,
            "total_onchain_footprint": crossmint_count,
            "source": "bundlebear",
            "confidence": "medium",
            "bundlebear_labels": {"erc4337": BUNDLEBEAR_CROSSMINT_FACTORY_LABEL},
            "note": "上界估计：factory 0xd703aae...（ZeroDev Kernel）含 Crossmint + 其他 Kernel 客户。测试网 Crossmint 占 67%。",
        }
        log_info("onchain data", provider=CROSSMINT_PROVIDER_ID,
                 erc4337=crossmint_count, confidence="medium-upper-bound")
    else:
        providers[CROSSMINT_PROVIDER_ID] = {
            "trackable": "partial",
            "erc4337_active_wallets_30d": None,
            "eip7702_live_accounts": None,
            "total_onchain_footprint": None,
            "error": "BundleBear API fetch failed",
            "source": "bundlebear",
        }

    # 5. 不可追踪供应商
    all_provider_ids = ["privy", "coinbase", "crossmint", "bnbchain_mcp", "moonpay", "minara"]
    for pid in all_provider_ids:
        if pid not in providers:
            providers[pid] = {
                "trackable": False,
                "erc4337_active_wallets_30d": None,
                "eip7702_live_accounts": None,
                "total_onchain_footprint": None,
                "reason": ONCHAIN_NOT_TRACKABLE.get(pid, "unknown"),
            }

    for provider in providers.values():
        if provider.get("trackable") is True or provider.get("trackable") == "partial":
            provider["active_wallets_30d"] = provider.get("total_onchain_footprint")

    return {
        "schema_version": "3.0",
        "source": "bundlebear",
        "collected_at": now,
        "period": "last-30d",
        "data_freshness": {
            "sla": "T+1",
            "latest_data_month": latest_month,
            "collection_status": "success",
        },
        "stale": False,
        "stale_since": None,
        "providers": providers,
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def _safe_write(path: Path, data: dict) -> bool:
    """Write JSON atomically. Returns True on success.

    If *data* represents a total failure (all provider values are null /
    errored), the existing file is preserved.
    """
    providers = data.get("providers", {})
    if not providers:
        log_error("empty providers — skipping write", path=str(path))
        return False

    # Check for total failure: every provider has an error key or all values null
    all_failed = all(
        p.get("error") is not None
        or (p.get("partial") is True and _all_values_null(p))
        for p in (providers.values() if isinstance(providers, dict) else providers)
    )
    if all_failed:
        log_error(
            "all providers failed — preserving previous file",
            path=str(path),
        )
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    try:
        with open(tmp, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        tmp.replace(path)
        log_info("wrote file", path=str(path.relative_to(REPO_ROOT)))
        return True
    except Exception as exc:
        log_error("file write failed", path=str(path), error=str(exc))
        if tmp.exists():
            tmp.unlink()
        return False


def _all_values_null(provider: dict) -> bool:
    """True only if there is genuinely no usable data."""
    # Check sub-items first — any successful child means data exists
    for key in ("packages", "repos"):
        items = provider.get(key, [])
        if any(
            item.get("weekly_downloads") is not None
            or item.get("stars") is not None
            or item.get("commits_30d") is not None
            for item in items
        ):
            return False
    # Check top-level numeric fields
    skip = {"error", "partial", "note", "status_page_url", "packages",
            "repos", "paths_checked", "breaking_change_ratio"}
    return all(v is None for k, v in provider.items() if k not in skip)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    log_info("collection started")
    ok_count = 0
    total = 6

    # 1. npm
    log_info("collecting npm downloads")
    npm_data = collect_npm()
    if _safe_write(OUTPUT_NPM, npm_data):
        ok_count += 1

    # 2. PyPI
    log_info("collecting pypi downloads")
    pypi_data = collect_pypi()
    if _safe_write(OUTPUT_PYPI, pypi_data):
        ok_count += 1

    # 3. GitHub
    log_info("collecting github activity")
    github_data = collect_github()
    if _safe_write(OUTPUT_GITHUB, github_data):
        ok_count += 1

    # 4. Status pages
    log_info("collecting status page data")
    status_data = collect_status()
    if _safe_write(OUTPUT_STATUS, status_data):
        ok_count += 1

    # 5. Docs density
    log_info("collecting docs/changelog density")
    docs_data = collect_docs()
    if _safe_write(OUTPUT_DOCS, docs_data):
        ok_count += 1

    # 6. On-chain data (BundleBear)
    log_info("collecting on-chain wallet activity")
    onchain_data = collect_onchain()
    if _safe_write(OUTPUT_ONCHAIN, onchain_data):
        ok_count += 1

    log_info("collection finished", ok=ok_count, total=total)

    if ok_count == 0:
        print("ERROR: all collectors failed — no files written", file=sys.stderr)
        sys.exit(1)
    elif ok_count < total:
        print(
            f"WARNING: {total - ok_count}/{total} collectors had issues",
            file=sys.stderr,
        )
        # Still exit 0 — partial data is committed; full failure is exit 1
    else:
        print(f"All {total} collectors succeeded", file=sys.stderr)


if __name__ == "__main__":
    main()
