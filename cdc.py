#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requires-Python: >=3.10

"""
Flink CDC PRs Scanner
"""

import csv
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple

from core.api import GitHubRESTCrawler
from core.config import GITHUB_TOKEN_DEFAULT

GITHUB_REPO_OWNER = "apache"
GITHUB_REPO_NAME = "flink-cdc"
OUTPUT_DIR = "cdc_output"
START_TIMESTAMP = datetime(2024, 3, 5, 0, 0, 0, tzinfo=timezone.utc)
TITLE_PATTERN = re.compile(r"\[[A-Z]+-\d+\]")
API_CALL_DELAY = 0.3  # seconds
METRIC_HEADERS = [
    "Bug编号",
    "tool_merged_at",
    "tool_merge_commit_hash",
    "tool_labels",
    "tool_files_changed",
    "tool_count_comments",
    "tool_total_chars",
    "tool_total_words",
    "tool_total_bytes",
]
METRIC_OUTPUT_PATH = "bugs-tool-generate.csv"


def read_select_bug_ids(filepath: str = "select_bugs.txt") -> list[str]:
    bug_ids = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip().strip('"').strip()
            if line.startswith("FLINK-"):
                bug_ids.append(line)
    return bug_ids


def extract_bug_id_from_title(title: str) -> str | None:
    match = TITLE_PATTERN.search(title or "")
    if match is None:
        return None
    return match.group(0).strip("[]")


def get_all_pulls(crawler: GitHubRESTCrawler) -> list[dict]:
    """Collect every pull request via paging and persist JSON snapshots for each page."""
    per_page = 100
    page_number = 1
    collected: list[dict] = []

    while True:
        # Walk every page of pull requests so we do not miss older entries.
        pulls = crawler.list_repo_pulls(
            state="all",
            sort="created",
            direction="asc",
            per_page=per_page,
            page=page_number,
        )
        if not pulls:
            break
        collected.extend(pulls)
        page_number += 1
    print(f"✅ Collected {len(collected)} pull requests from GitHub")
    return collected


def load_local_pull_pages(output_dir: str) -> list[dict]:
    """Load previously saved pull request pages from disk."""
    base = Path(output_dir)
    if not base.exists():
        return []
    pulls: list[dict] = []
    for path in sorted(base.glob("repo_pulls_page_*_per_*.json")):
        with path.open("r", encoding="utf-8") as handle:
            pulls.extend(json.load(handle))
    if pulls:
        print(f"✅ Loaded {len(pulls)} pull requests from local cache")
    return pulls


def ensure_pull_dataset(crawler: GitHubRESTCrawler) -> list[dict]:
    """Prefer cached pull requests; fall back to live collection when necessary."""
    local_cached = load_local_pull_pages(OUTPUT_DIR)
    if local_cached:
        return local_cached
    return get_all_pulls(crawler)


def filter_pulls(raw_pulls: list[dict]) -> list[dict]:
    """Apply project-specific constraints to narrow down pull requests of interest."""

    def _within_window(pr: dict) -> bool:
        created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        return created_at >= START_TIMESTAMP

    def _matches_title_in_bug_ids(pr: dict, bug_ids: list) -> bool:
        match = TITLE_PATTERN.search(pr["title"])
        if match is None:
            return False
        bug_id = match.group(0)
        # with '[' ']'
        return bug_id.strip('[').strip(']') in bug_ids

    bug_ids = read_select_bug_ids()
    filtered = [
        pr
        for pr in raw_pulls
        if _within_window(pr) and _matches_title_in_bug_ids(pr, bug_ids)
    ]
    print(
        f"✅ Filtered out {len(raw_pulls) - len(filtered)} pull requests (kept {len(filtered)})"
    )
    return filtered


def _load_cached_issue_comments(pull_number: int) -> Tuple[list[dict], bool]:
    """Return cached issue comments and a flag indicating whether cache files existed."""
    base = Path(OUTPUT_DIR)
    page = 1
    cached_comments: list[dict] = []
    cache_hit = False
    while True:
        path = base / f"issue_{pull_number}_comments_page_{page}.json"
        if not path.exists():
            break
        cache_hit = True
        with path.open("r", encoding="utf-8") as fh:
            cached_comments.extend(json.load(fh))
        page += 1
    return cached_comments, cache_hit


def _load_cached_pull_files(pull_number: int) -> Tuple[list[dict], bool]:
    """Return cached file-change payloads and whether cache files existed."""
    base = Path(OUTPUT_DIR)
    page = 1
    cached_files: list[dict] = []
    cache_hit = False
    while True:
        path = base / f"pull_{pull_number}_files_page_{page}.json"
        if not path.exists():
            break
        cache_hit = True
        with path.open("r", encoding="utf-8") as fh:
            cached_files.extend(json.load(fh))
        page += 1
    return cached_files, cache_hit


def _load_existing_metrics(csv_path: Path) -> list[dict]:
    """Read metrics CSV into dictionaries while preserving order."""
    if not csv_path.exists():
        return []
    rows: list[dict] = []
    with csv_path.open("r", newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        header: list[str] | None = None
        for raw_row in reader:
            if header is None:
                if any(cell.strip() for cell in raw_row):
                    header = raw_row
                continue
            if not raw_row or not any(cell.strip() for cell in raw_row):
                continue
            if len(raw_row) < len(METRIC_HEADERS):
                raw_row.extend([""] * (len(METRIC_HEADERS) - len(raw_row)))
            row_dict = {key: value for key, value in zip(header, raw_row)}
            normalized = {key: row_dict.get(key, "") for key in METRIC_HEADERS}
            rows.append(normalized)
    return rows




# TODO Need implementation of `list_review_comments`/`list_pull_comments`
def collect_review_comments():
    pass


def collect_issue_comments(
    crawler: GitHubRESTCrawler, pull_number: int
) -> dict[str, int]:
    """
    Gather comment statistics for a pull request.
    Prefer cached pages and only hit the API when data is missing.
    """
    per_page = 100
    total_chars = total_words = total_bytes = 0
    comments, cached = _load_cached_issue_comments(pull_number)

    if not cached:
        page = 1
        while True:
            batch = crawler.list_issue_comments(
                pull_number,
                per_page=per_page,
                page=page,
            )
            if not batch:
                break
            comments.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
            time.sleep(API_CALL_DELAY)

    for comment in comments:
        text = str(comment.get("body") or "").strip()
        total_chars += len(text)
        total_words += len(text.split())
        total_bytes += len(text.encode("utf-8"))

    return {
        "count_comments": len(comments),
        "total_chars": total_chars,
        "total_words": total_words,
        "total_bytes": total_bytes,
    }


def collect_files_changed(crawler: GitHubRESTCrawler, pull_number: int) -> list[str]:
    """
    Return filenames touched by a pull request, leveraging cached data when available.
    """
    per_page = 100
    pr_files, cached = _load_cached_pull_files(pull_number)

    if not cached:
        page = 1
        while True:
            batch = crawler.list_pull_files(
                pull_number,
                per_page=per_page,
                page=page,
            )
            if not batch:
                break
            pr_files.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
            time.sleep(API_CALL_DELAY)

    return [f.get("filename", "N/A") for f in pr_files]


def collect_labels(pr: dict) -> list[str]:
    return [l.get("name", "N/A") for l in pr.get("labels", [])]


def summarize_pulls(crawler: GitHubRESTCrawler, pulls: list[dict], csv_path: str) -> None:
    """Output key pull request metadata in a compact table."""
    if not pulls:
        print("No pull requests matched the filter criteria.")
        return
    csv_location = Path(csv_path)
    rows = _load_existing_metrics(csv_location)
    rows_by_bug = {
        existing.get("Bug编号", ""): existing
        for existing in rows
        if existing.get("Bug编号")
    }
    for pr in pulls:
        pull_number = pr.get("number", 0)
        title = pr.get("title", "UNKNOWN")
        sha = pr.get("merge_commit_sha", None)
        merged_at = pr.get("merged_at", None)
        labels = collect_labels(pr)
        files_changed = collect_files_changed(crawler, pull_number)
        time.sleep(API_CALL_DELAY)
        comments_detail = collect_issue_comments(crawler, pull_number)
        bug_id = extract_bug_id_from_title(title)
        if bug_id:
            metrics_row = {
                "tool_merged_at": merged_at or "",
                "tool_merge_commit_hash": sha or "",
                "tool_labels": ";".join(labels) if labels else "",
                "tool_files_changed": ";".join(files_changed) if files_changed else "",
                "tool_count_comments": str(comments_detail.get("count_comments", 0)),
                "tool_total_chars": str(comments_detail.get("total_chars", 0)),
                "tool_total_words": str(comments_detail.get("total_words", 0)),
                "tool_total_bytes": str(comments_detail.get("total_bytes", 0)),
            }
            row = rows_by_bug.get(bug_id)
            if row is None:
                row = {key: "" for key in METRIC_HEADERS}
                row["Bug编号"] = bug_id
                rows.append(row)
                rows_by_bug[bug_id] = row
            row.update(metrics_row)
        print(
            f"- {title}\n  merge_commit_sha: {sha}\n  merged_at: {merged_at}\n  labels: {labels}\n  files_changed: {files_changed}\n  comments_detail: {comments_detail}"
        )
    csv_location.parent.mkdir(parents=True, exist_ok=True)
    with csv_location.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(METRIC_HEADERS)
        for row in rows:
            writer.writerow([row.get(key, "") for key in METRIC_HEADERS])


def main():
    crawler = GitHubRESTCrawler(
        owner=GITHUB_REPO_OWNER,
        repo=GITHUB_REPO_NAME,
        token=GITHUB_TOKEN_DEFAULT,
        output_dir=OUTPUT_DIR,
    )
    try:
        pulls = ensure_pull_dataset(crawler)
        filtered = filter_pulls(pulls)
        summarize_pulls(crawler, filtered, csv_path=METRIC_OUTPUT_PATH)
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
