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
TITLE_PATTERN = re.compile(r"FLINK-\d{5}")
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


def filter_pulls(raw_pulls: list[dict]) -> list[dict]:
    """Apply project-specific constraints to narrow down pull requests of interest."""

    def _within_window(pr: dict) -> bool:
        created_at = datetime.fromisoformat(pr["created_at"].replace("Z", "+00:00"))
        return created_at >= START_TIMESTAMP

    def _matches_title_in_bug_ids(pr: dict, bug_ids: list) -> bool:
        match = TITLE_PATTERN.search(pr.get("title") or "")
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

    return filtered


def _load_cached_template(
    filename_template: str,
    *,
    paginated: bool = True,
    base_dir: str | Path = OUTPUT_DIR,
) -> Tuple[list[dict], bool]:
    """
    Generic loader for cached API responses.
    Supports paginated cache files (template must contain {page}) or single-file caches.
    """
    base = Path(base_dir)
    if not base.exists():
        return [], False

    cache_hit = False
    records: list[dict] = []

    if paginated:
        page = 1
        while True:
            path = base / filename_template.format(page=page)
            if not path.exists():
                break
            cache_hit = True
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    records.extend(data)
                elif data is not None:
                    records.append(data)
            page += 1
    else:
        path = base / filename_template
        if path.exists():
            cache_hit = True
            with path.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    records.extend(data)
                elif data is not None:
                    records.append(data)

    return records, cache_hit


def _load_cached_repo_pulls(per_page: int = 100) -> Tuple[list[dict], bool]:
    """Return cached repo pull requests and a flag indicating whether cache files existed."""
    return _load_cached_template(f"repo_pulls_page_{{page}}_per_{per_page}.json")


def _load_cached_pull_request(pull_number: int) -> Tuple[dict, bool]:
    """Return cached pull request detail and whether a cache entry existed."""
    cached_list, cached_hit = _load_cached_template(
        f"pull_{pull_number}.json", paginated=False
    )
    if not cached_hit:
        return {}, False
    if len(cached_list) > 1 or cached_list == []:
        print(
            f"⚠️ Local cache file pull_{pull_number}.json exist but load fail. Please check"
        )
        return {}, False
    return cached_list[0], True


def _load_cached_issue_comments(pull_number: int) -> Tuple[list[dict], bool]:
    """Return cached issue comments and a flag indicating whether cache files existed."""
    return _load_cached_template(f"issue_{pull_number}_comments_page_{{page}}.json")


def _load_cached_review_comments(pull_number: int) -> Tuple[list[dict], bool]:
    """Return cached review comments and a flag indicating whether cache files existed."""
    return _load_cached_template(
        f"pull_{pull_number}_review_comments_None_page_{{page}}.json"
    )


def _load_cached_review_blocs(pull_number: int) -> Tuple[list[dict], bool]:
    """Return cached pull reviews and a flag indicating whether cache files existed."""
    return _load_cached_template(f"pull_{pull_number}_reviews_page_{{page}}.json")


def _load_cached_pull_files(pull_number: int) -> Tuple[list[dict], bool]:
    """Return cached file-change payloads and whether cache files existed."""
    return _load_cached_template(f"pull_{pull_number}_files_page_{{page}}.json")


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
            if (
                base_name == "apache:master" or base_name == "master"
            ) and base_login == "apache":
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


def _collect_from_cache_or_api(
    load_cache_fn,
    crawler: GitHubRESTCrawler,
    api_method_name: str,
    pull_number: int,
    per_page: int = 100,
    *,
    filter_fn=None,
    api_call_delay: float = 0.5,
) -> list[dict]:
    """
    Data collection helper:
    1. Try to load cached data: `load_cache_fn(pull_number) -> (cached_items, cache_hit: bool)`
    2. If no cache is available (cache_hit=False), fetch data from the GitHub API
       using crawler.{api_method_name}(pull_number, per_page=..., page=N),
       automatically handling pagination and accumulating all pages.
    3. Optionally apply filter_fn to the combined results
    Returns:
    A list of dictionaries representing the collected data.
    """

    # --- Step 1: Load cache ---
    cached, cache_hit = load_cache_fn(pull_number)
    results: list[dict] = list(cached)

    # --- Step 2: Call api if cache not exist ---
    if not cache_hit:
        api_fn = getattr(crawler, api_method_name)
        page = 1

        while True:
            batch = api_fn(pull_number, per_page=per_page, page=page)
            time.sleep(api_call_delay)

            if not batch:
                break

            results.extend(batch)

            if len(batch) < per_page:
                break

            page += 1

    # --- Step 3: Filter ---
    if filter_fn is not None:
        results = [item for item in results if filter_fn(item)]

    return results


def get_repo_pulls(crawler: GitHubRESTCrawler, per_page: int = 100) -> list[dict]:
    """Collect every pull request via paging and persist JSON snapshots for each page."""
    page = 1
    collected: list[dict] = []

    while True:
        # Walk every page of pull requests so we do not miss older entries.
        batch = crawler.list_repo_pulls(
            state="all",
            sort="created",
            direction="asc",
            per_page=per_page,
            page=page,
        )
        collected.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    print(f"✅ Collected {len(collected)} pull requests from GitHub")
    return collected


def collect_repo_pulls(
    crawler: GitHubRESTCrawler, use_cache: bool = True
) -> list[dict]:
    """Prefer cached pull requests; fall back to live collection when necessary."""
    # TODO update _collect_from_cache_or_api to support collect_repo_pulls
    if use_cache:
        print("Use local cache to get repo pull requests.")
        local_cached_repo_pulls, cached_hit = _load_cached_repo_pulls()
        print(
            f"✅ Collected {len(local_cached_repo_pulls)} repo pull requests from local cache"
        )
        if cached_hit and local_cached_repo_pulls != []:
            return local_cached_repo_pulls
    # Fallback to use api to get all pulls
    return get_repo_pulls(crawler)


def collect_get_pr_detail(crawler: GitHubRESTCrawler, pull_number: int):
    """
    Gather needed pr detail from pull request itself
    """
    pr_detail_title_chars = pr_detail_body_chars = 0
    pr_detail_comments_count = pr_detail_review_comments_count = 0

    pr_detail, cached = _load_cached_pull_request(pull_number)
    if not cached:
        pr_detail = crawler.get_pull(pull_number)

    pr_title = pr_detail.get("title", "")
    if pr_title is None:
        pr_title = ""
    pr_body = pr_detail.get("body", "")
    if pr_body is None:
        pr_body = ""
    pr_detail_title_chars = len(pr_title.strip())
    pr_detail_body_chars = len(pr_body.strip())
    pr_detail_comments_count = pr_detail.get("comments", 0)
    pr_detail_review_comments_count = pr_detail.get("review_comments", 0)
    return {
        "pr_detail_title_chars": pr_detail_title_chars,
        "pr_detail_body_chars": pr_detail_body_chars,
        "pr_detail_comments_count": pr_detail_comments_count,
        "pr_detail_review_comments_count": pr_detail_review_comments_count,
    }


def collect_files_changed(crawler: GitHubRESTCrawler, pull_number: int) -> list[str]:
    """
    Return filenames touched by a pull request, leveraging cached data when available.
    """

    def _load_cache(pn: int):
        return _load_cached_pull_files(pn)

    per_page = 100
    # pr_files, cached = _load_cached_pull_files(pull_number)
    # Try common useful util function
    pr_files = _collect_from_cache_or_api(
        load_cache_fn=_load_cache,
        crawler=crawler,
        api_method_name="list_pull_files",
        pull_number=pull_number,
        per_page=per_page,
    )
    # Solve data
    return list(filter(None, [f.get("filename") for f in pr_files]))


def collect_labels(pr: dict) -> list[str]:
    return list(filter(None, [l.get("name") for l in pr.get("labels", [])]))


def collect_issue_comments(
    crawler: GitHubRESTCrawler, pull_number: int
) -> dict[str, int]:
    """
    Gather comment statistics for a pull request.
    Prefer cached pages and only hit the API when data is missing.
    """

    def _load_cache(pn: int):
        return _load_cached_issue_comments(pn)

    per_page = 100
    # Try common useful util function
    issue_comments = _collect_from_cache_or_api(
        load_cache_fn=_load_cache,
        crawler=crawler,
        api_method_name="list_issue_comments",
        pull_number=pull_number,
        per_page=per_page,
    )
    # Solve data
    issue_comments_chars = issue_comments_words = issue_comments_bytes = 0
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

    def _load_cache(pn: int):
        return _load_cached_review_comments(pn)

    per_page = 100
    # Try common useful util funciton
    review_comments = _collect_from_cache_or_api(
        load_cache_fn=_load_cache,
        crawler=crawler,
        api_method_name="list_pull_review_comments",
        pull_number=pull_number,
        per_page=per_page,
    )
    # Solve data
    review_comments_chars = review_comments_words = review_comments_bytes = 0
    for comment in review_comments:
        text = str(comment.get("body", "").strip())
        review_comments_chars += len(text)
        review_comments_words += len(text.split())
        review_comments_bytes += len(text.encode("utf-8"))

    return {
        "review_comments_count": len(review_comments),
        "review_comments_chars": review_comments_chars,
        "review_comments_words": review_comments_words,
        "review_comments_bytes": review_comments_bytes,
    }


def collect_review_blocs(crawler: GitHubRESTCrawler, pull_number: int):
    """
    Gather review detail(body) for a pull request.
    """

    def _load_cache(pn: int):
        return _load_cached_review_blocs(pn)

    per_page = 100
    # Try common useful util funciton
    review_blocs = _collect_from_cache_or_api(
        load_cache_fn=_load_cache,
        crawler=crawler,
        api_method_name="list_pull_reviews",
        pull_number=pull_number,
        per_page=per_page,
        filter_fn=lambda x: (x.get("body") or "").strip() != "",
    )
    # Solve data
    review_blocs_chars = review_blocs_words = review_blocs_bytes = 0
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
                    "Pull request should only consider head branch or base branch."
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
        }
        new_row |= head_detail
        new_row |= base_detail
        new_row |= pr_detail
        new_row |= issue_comments_detail
        new_row |= review_comments_detail
        new_row |= review_blocs_detail
        new_row["tool_total_comments_count"] = (
            # more reasonable for get from pr_detail (some outdated or deleted comments)
            new_row["issue_comments_count"]
            + new_row["review_comments_count"]
            + new_row["review_blocs_count"]
        )
        new_row["tool_total_chars"] = (
            new_row["issue_comments_chars"]
            + new_row["review_comments_chars"]
            + new_row["review_blocs_chars"]
        )
        new_row["tool_total_words"] = (
            new_row["issue_comments_words"]
            + new_row["review_comments_words"]
            + new_row["review_blocs_words"]
        )
        new_row["tool_total_bytes"] = (
            new_row["issue_comments_bytes"]
            + new_row["review_comments_bytes"]
            + new_row["review_blocs_bytes"]
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
        raw_pulls = collect_repo_pulls(crawler, use_cache=True)
        filtered = filter_pulls(raw_pulls)
        summarize_pulls(
            crawler, pulls=filtered, csv_path=METRIC_OUTPUT_PATH, force_update=False
        )
    except Exception as e:
        print(f"Error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
