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
from typing import Tuple, Set

from core.api import GitHubRESTCrawler
from core.config import GITHUB_TOKEN_DEFAULT

GITHUB_REPO_OWNER = "apache"
GITHUB_REPO_NAME = "flink-cdc"
OUTPUT_DIR = "cdc_output"
START_TIMESTAMP = datetime(2024, 3, 5, 0, 0, 0, tzinfo=timezone.utc)
TITLE_PATTERN = re.compile(r"\[[A-Z]+-\d+\]")
API_CALL_DELAY = 0.5  # seconds
METRIC_HEADERS = [
    "bug_id",
    "tool_created_at",
    "tool_updated_at",
    "tool_closed_at",
    "tool_merged_at",
    "tool_merge_commit_hash",
    "tool_labels",
    "tool_files_changed",
    "tool_total_comments_count",
    "tool_total_chars",
    "tool_total_words",
    "tool_total_bytes",
    "issue_comments_count",
    "issue_comments_chars",
    "issue_comments_words",
    "issue_comments_bytes",
    "review_comments_count",
    "review_comments_chars",
    "review_comments_words",
    "review_comments_bytes",
    "pr_detail_title_chars",
    "pr_detail_body_chars",
    "pr_detail_comments_count",
    "pr_detail_review_comments_count",
    "review_blocs_count",
    "review_blocs_chars",
    "review_blocs_words",
    "review_blocs_bytes",
]
METRIC_OUTPUT_PATH = "cdc_output/csv/"


def read_select_bug_ids(filepath: str) -> list[str]:
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
    return match.group(0).strip("[ ]")


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
        return bug_id.strip("[ ]") in bug_ids

    bug_ids = read_select_bug_ids(filepath="cdc_output/select_bugs.txt")
    filtered = [
        pr
        for pr in raw_pulls
        if _within_window(pr) and _matches_title_in_bug_ids(pr, bug_ids)
    ]
    print(
        f"✅ Filtered out {len(raw_pulls) - len(filtered)} pull requests (kept {len(filtered)})"
    )
    # tmp_list  = [a["title"] for a in filtered]
    # tmp_list.sort(key=lambda x: x[:13])
    # print ("\n".join(tmp_list))

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


def _load_cached_review_comments(pull_number: int) -> Tuple[list[dict], bool]:
    """Return cached review comments and a flag indicating whether cache files existed."""
    base = Path(OUTPUT_DIR)
    page = 1
    cached_comments: list[dict] = []
    cache_hit = False
    while True:
        path = base / f"pull_{pull_number}_review_comments_None_page_{page}.json"
        if not path.exists():
            break
        cache_hit = True
        with path.open("r", encoding="utf-8") as fh:
            cached_comments.extend(json.load(fh))
        page += 1
    return cached_comments, cache_hit


def _load_cached_review_blocs(pull_number: int) -> Tuple[list[dict], bool]:
    """Return cached pull reviews and a flag indicating whether cache files existed."""
    base = Path(OUTPUT_DIR)
    page = 1
    cached_reviews: list[dict] = []
    cache_hit = False
    while True:
        path = base / f"pull_{pull_number}_reviews_page_{page}.json"
        if not path.exists():
            break
        cache_hit = True
        with path.open("r", encoding="utf-8") as fh:
            cached_reviews.extend(json.load(fh))
        page += 1
    return cached_reviews, cache_hit


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


def _load_cached_pull_request(pull_number: int) -> Tuple[dict, bool]:
    """Return cached pull request detail and whether a cache entry existed."""
    base = Path(OUTPUT_DIR)
    path = base / f"pull_{pull_number}.json"
    if not path.exists():
        return {}, False
    with path.open("r", encoding="utf-8") as fh:
        pr_detail = json.load(fh)
    return pr_detail, True


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
                    if header != METRIC_HEADERS:
                        raise ValueError(
                            "The readed header is not euql to METRIC_HEADERS. Check it"
                        )
                continue
            if not raw_row or not any(cell.strip() for cell in raw_row):
                continue
            if len(raw_row) < len(METRIC_HEADERS):
                raw_row.extend([""] * (len(METRIC_HEADERS) - len(raw_row)))
            row_dict = {key: value for key, value in zip(header, raw_row)}
            normalized = {key: row_dict.get(key, "") for key in METRIC_HEADERS}
            rows.append(normalized)
    return rows


def _update_merge_append(
    mode: str, visited_merged: Set[str], old_row: dict, new_row: dict, append_rows: list
):
    """Inline update (merge) or append"""
    if mode == "update":
        # update in line and not add in append_rows
        old_row.clear()
        old_row.update(new_row)
    elif mode == "merge":
        # Only merge in output when the pull status is merged.
        # TODO make sure the base branch is master
        id = new_row.get("bug_id")
        if id is None:
            raise ValueError("'bug_id' in new row is None")
        is_merged_at_exist: bool = new_row.get("tool_merged_at") != ""
        if is_merged_at_exist:
            # Only one is merged and base branch is master
            base_name = new_row.get("base_name")
            base_login = new_row.get("base_login")
            if (base_name == "apache:master" or base_name == "master") and base_login == "apache":
                if id in visited_merged:
                    # raise ValueError(f"Double merge {id}")
                    print(f"Double merge {id}")
                    # TODO? add in append
                visited_merged.add(id)
                old_row.update(new_row)
            else:
                # Merged to other branch
                print(f"BP merge {id}, merged to {base_name}, user_login {base_login}")
                # abort now
        else:
            append_rows.append(new_row)


    elif mode == "append":
        # append in append_rows and do not change the old row
        id = new_row.get("bug_id")
        if id is None:
            raise ValueError("'bug_id' in new row is None")
        if id not in visited_merged:
            # First visit
            visited_merged.add(id)
            old_row.update(new_row)
        else:
            # Visited
            append_rows.append(new_row)
    else:
        raise ValueError("Unsupported mode in _check_if_append")


def write_rows_csv_file(final_path: Path, headers: list[str], rows: list):
    final_path.parent.mkdir(parents=True, exist_ok=True)
    with final_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([row.get(key, "") for key in headers])


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
            time.sleep(API_CALL_DELAY)
            if not batch:
                break
            pr_files.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

    return list(filter(None, [f.get("filename") for f in pr_files]))


def collect_labels(pr: dict) -> list[str]:
    return list(filter(None, [l.get("name") for l in pr.get("labels", [])]))

def collect_get_pr_detail(crawler: GitHubRESTCrawler, pull_number: int):
    """
    Gather needed pr detail from pull request itself
    """
    pr_detail_title_chars = pr_detail_body_chars = 0
    pr_detail_comments_count = pr_detail_review_comments_count = 0

    pr_detail, cached = _load_cached_pull_request(pull_number)
    if not cached:
        pr_detail = crawler.get_pull(pull_number)
        time.sleep(API_CALL_DELAY)
    # print(pr_detail)
    t = pr_detail.get("title","")
    if t is None:
        t = ""
    b = pr_detail.get("body","")
    if b is None:
        b = ""
    pr_detail_title_chars = len(t.strip())
    pr_detail_body_chars = len(b.strip())
    pr_detail_comments_count = pr_detail.get("comments", 0)
    pr_detail_review_comments_count = pr_detail.get("review_comments", 0)
    return {
        "pr_detail_title_chars": pr_detail_title_chars,
        "pr_detail_body_chars": pr_detail_body_chars,
        "pr_detail_comments_count": pr_detail_comments_count,
        "pr_detail_review_comments_count": pr_detail_review_comments_count,
    }

def collect_issue_comments(
    crawler: GitHubRESTCrawler, pull_number: int
) -> dict[str, int]:
    """
    Gather comment statistics for a pull request.
    Prefer cached pages and only hit the API when data is missing.
    """
    per_page = 100
    issue_comments_chars = issue_comments_words = issue_comments_bytes = 0
    issue_comments, cached = _load_cached_issue_comments(pull_number)

    if not cached:
        page = 1
        while True:
            batch = crawler.list_issue_comments(
                pull_number,
                per_page=per_page,
                page=page,
            )
            time.sleep(API_CALL_DELAY)
            if not batch:
                break
            issue_comments.extend(batch)
            if len(batch) < per_page:
                break
            page += 1

    for comment in issue_comments:
        text = str(comment.get("body") or "").strip()
        issue_comments_chars += len(text)
        issue_comments_words += len(text.split())
        issue_comments_bytes += len(text.encode("utf-8"))

    return {
        "issue_comments_count": len(issue_comments),
        "issue_comments_chars": issue_comments_chars,
        "issue_comments_words": issue_comments_words,
        "issue_comments_bytes": issue_comments_bytes,
    }

def collect_review_comments(crawler: GitHubRESTCrawler, pull_number: int):
    """
    Gather review commets for a pull request.
    """
    per_page = 100
    review_comments_chars = review_comments_words = review_comments_bytes = 0
    review_comments, cached = _load_cached_review_comments(pull_number)
    if not cached:
        page = 1
        while True:
            batch = crawler.list_pull_review_comments(
                pull_number, per_page=per_page, page=page
            )
            time.sleep(API_CALL_DELAY)
            if not batch:
                break
            review_comments.extend(batch)
            if len(batch) < per_page:
                break
            page += 1
    for comment in review_comments:
        text = str(comment.get("body","").strip())
        review_comments_chars += len(text)
        review_comments_words += len(text.split())
        review_comments_bytes += len(text.encode("utf-8"))

    return {
        "review_comments_count": len(review_comments),
        "review_comments_chars": review_comments_chars,
        "review_comments_words": review_comments_words,
        "review_comments_bytes": review_comments_bytes,
    }


def collect_review_blocs(crawler: GitHubRESTCrawler,pull_number: int):
    """
    Gather review detail(body) for a pull request.
    """
    per_page = 100
    review_blocs, cached = _load_cached_review_blocs(pull_number)
    review_blocs_chars = review_blocs_words = review_blocs_bytes = 0

    if not cached:
        page = 1
        while True:
            batch = crawler.list_pull_reviews(
                pull_number, per_page=per_page, page=page
            )
            time.sleep(API_CALL_DELAY)
            if not batch:
                break
            # Filter review bloc with body
            filtered = [
                x
                for x in batch
                if (x.get("body") or "").strip() != ""
            ]
            review_blocs.extend(filtered)
            if len(batch) < per_page:
                break
            page += 1

    # Ensure only reviews with non-empty body are considered,
    # regardless of whether they came from cache or live API calls.
    review_blocs = [
        bloc
        for bloc in review_blocs
        if (bloc.get("body") or "").strip() != ""
    ]

    for bloc in review_blocs:
        text = (bloc.get("body") or "").strip()
        review_blocs_chars += len(text)
        review_blocs_words += len(text.split())
        review_blocs_bytes += len(text.encode("utf-8"))

    return {
        "review_blocs_count": len(review_blocs),
        "review_blocs_chars": review_blocs_chars,
        "review_blocs_words": review_blocs_words,
        "review_blocs_bytes": review_blocs_bytes,
    }






def summarize_pulls(
    crawler: GitHubRESTCrawler,
    pulls: list[dict],
    csv_path: str,
    force_update: bool = False,
) -> None:
    """Output key pull request metadata in a compact table."""
    if not pulls:
        print("No pull requests matched the filter criteria.")
        return
    input_csv = Path(csv_path) / "input.csv"
    rows = _load_existing_metrics(input_csv)
    rows_by_bug_hashmap = {
        existing.get("bug_id", ""): existing
        for existing in rows
        if existing.get("bug_id")
    }
    rows_visited_merged: Set[str] = set()
    not_included_rows: list[dict] = []
    append_rows: list[dict] = []
    for pr in pulls:
        pull_number: int | None = pr.get("number")
        if pull_number is None:
            raise ValueError(f"Missing 'number' field in pull request object.")
        title: str | None = pr.get("title")
        if title is None:
            raise ValueError(f"Missing 'title' field in pull request object.")
        bug_id: str | None = extract_bug_id_from_title(title)
        if bug_id is None:
            # Has title filed but not include FLINK-XXXX
            print(f"⚠️ WARN: pull request with title: {title} should be filtered")
            continue
        hash: str | None = pr.get("merge_commit_sha")
        created_at: str | None = pr.get("created_at")
        updated_at: str | None = pr.get("updated_at")
        closed_at: str | None = pr.get("closed_at")
        merged_at: str | None = pr.get("merged_at")
        labels: list[str] = collect_labels(pr)

        def _get_branch_name_and_login(pr: dict, where: str):
            """
            Get head/base branch name and login
            """
            if where != "head" and where != "base":
                raise ValueError(
                    "Pull request only consider head branch or base branch."
                )
            b = pr.get(where, None)
            if b is None:
                raise ValueError(f"Branch {where} is None. Double check it.")
            name = b.get("label")
            if name is None:
                raise ValueError(f"Branch {where}.label is None. Double check it.")
            user = b.get("user")
            if user is None:
                raise ValueError(f"Branch {where}.user is None. Double check it.")
            login = user.get("login")
            if login is None:
                raise ValueError(f"Branch {where}.user.login is None. Double check it.")
            return {
                f"{where}_name": name,
                f"{where}_login": login,
            }

        head_detail: dict[str, str] = _get_branch_name_and_login(pr, "head")
        base_detail: dict[str, str] = _get_branch_name_and_login(pr, "base")
        # Call other APIs
        pr_detail: dict = collect_get_pr_detail(crawler, pull_number)
        files_changed: list[str] = collect_files_changed(crawler, pull_number)
        issue_comments_detail = collect_issue_comments(crawler, pull_number)
        review_comments_detail = collect_review_comments(crawler, pull_number)
        review_blocs_detail = collect_review_blocs(crawler, pull_number)

        # Must Including FLINK-XXXX
        new_row = {
            "bug_id": bug_id,
            "tool_created_at": created_at or "",
            "tool_updated_at": updated_at or "",
            "tool_closed_at": closed_at or "",
            "tool_merged_at": merged_at or "",
            "tool_merge_commit_hash": hash or "",
            "tool_labels": ";".join(labels),
            "tool_files_changed": ";".join(files_changed),
            # "tool_total_comments_count": str(issue_comments_detail.get("count_comments", 0)),
            # "tool_total_chars": str(issue_comments_detail.get("total_chars", 0)),
            # "tool_total_words": str(issue_comments_detail.get("total_words", 0)),
            # "tool_total_bytes": str(issue_comments_detail.get("total_bytes", 0)),
            # "issue_comments_count": issue_comments_detail.get(
            #     "issue_comments_count", 0
            # ),
            # "issue_comments_chars": issue_comments_detail.get(
            #     "issue_comments_chars", 0
            # ),
            # "issue_comments_words": issue_comments_detail.get(
            #     "issue_comments_words", 0
            # ),
            # "issue_comments_bytes": issue_comments_detail.get(
            #     "issue_comments_bytes", 0
            # ),
            # "review_comments_count": review_comments_detail.get(
            #     "review_comments_count", 0
            # ),
            # "review_comments_chars": review_comments_detail.get(
            #     "review_comments_chars", 0
            # ),
            # "review_comments_words": review_comments_detail.get(
            #     "review_comments_words", 0
            # ),
            # "review_comments_bytes": review_comments_detail.get(
            #     "review_comments_bytes", 0
            # ),
        }
        new_row |= head_detail
        new_row |= base_detail
        new_row |= pr_detail
        new_row |= issue_comments_detail
        new_row |= review_comments_detail
        new_row |= review_blocs_detail
        new_row["tool_total_comments_count"] = (
            # more reasonable for get from pr_detail (some outdated or deleted comments)
            new_row["issue_comments_count"] + new_row["review_comments_count"] + new_row["review_blocs_count"]
        )
        new_row["tool_total_chars"] = (
            new_row["issue_comments_chars"] + new_row["review_comments_chars"] + new_row["review_blocs_chars"]
        )
        new_row["tool_total_words"] = (
            new_row["issue_comments_words"] + new_row["review_comments_words"] + new_row["review_blocs_words"]
        )
        new_row["tool_total_bytes"] = (
            new_row["issue_comments_bytes"] + new_row["review_comments_bytes"] + new_row["review_blocs_bytes"]
        )

        row = rows_by_bug_hashmap.get(bug_id)
        if row is None:
            # Not in manual bug list add to `not_included.csv`
            not_included_rows.append(new_row)
        else:
            # In manual bug list
            if force_update:
                # force update local cache (final write)
                _update_merge_append(
                    mode="update",
                    visited_merged=rows_visited_merged,
                    old_row=row,
                    new_row=new_row,
                    append_rows=append_rows,
                )
            else:
                _update_merge_append(
                    mode="merge",
                    visited_merged=rows_visited_merged,
                    old_row=row,
                    new_row=new_row,
                    append_rows=append_rows,
                )

    write_rows_csv_file(
        final_path=Path(csv_path) / "output.csv", headers=METRIC_HEADERS, rows=rows
    )
    write_rows_csv_file(
        final_path=Path(csv_path) / "not_included.csv",
        headers=METRIC_HEADERS,
        rows=not_included_rows,
    )
    write_rows_csv_file(
        final_path=Path(csv_path) / "append.csv",
        headers=METRIC_HEADERS,
        rows=append_rows,
    )


def main():
    crawler = GitHubRESTCrawler(
        owner=GITHUB_REPO_OWNER,
        repo=GITHUB_REPO_NAME,
        token=GITHUB_TOKEN_DEFAULT,
        output_dir=OUTPUT_DIR,
    )
    try:
        raw_pulls = ensure_pull_dataset(crawler)
        filtered = filter_pulls(raw_pulls)
        summarize_pulls(
            crawler, pulls=filtered, csv_path=METRIC_OUTPUT_PATH, force_update=False
        )
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
