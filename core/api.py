#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Requires-Python: >=3.10

"""
GitHub API Crawler Implementation
Implements various common APIs for REST API and gh CLI based crawlers.
Authors: edwardzcn
"""

import logging
import requests
from pathlib import Path
from typing import Any
from .model import GitHubCore
from .config import SupportMediaTypes

logger = logging.getLogger(__name__)


class GitHubRESTCrawler(GitHubCore):
    """GitHub REST API implementation of GitHubCrawlerBase"""

    def __init__(
        self,
        owner: str | None,
        repo: str | None = None,
        token: str | None = None,
        output_dir: str | None = None,
        session: requests.Session | None = None,
    ):
        super().__init__(owner, repo, token, output_dir, session=session)

    # --------------------------------------------------------
    # REST API Endpoints
    # --------------------------------------------------------
    # Actions
    ## Artifacts
    def list_repo_artifacts(
        self, per_page: int = 30, page: int = 1, name: str | None = None
    ) -> dict[str, Any]:
        """
        Get artifacts for a repository
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#list-artifacts-for-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/artifacts"
        params: dict[str, Any] = {
            "per_page": per_page,
            "page": page,
        }
        if name is not None:
            params["name"] = name
        resp = self._get(url, params=params)
        data = resp.json()
        total = data.get("total_count")
        self._persist(
            data,
            # TODO configurable repo owner, repo name
            filename="repo_artifacts.json",
            post_msg=f"Fetched {total} artifacts in repo:{self.repo_name}",
        )
        return data

    def get_artifact(self, artifact_id: int) -> dict[str, Any]:
        """
        Get a single artifact by ID.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#get-an-artifact
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/actions/artifacts/{artifact_id}"
        )
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"artifact_{artifact_id}.json",
            post_msg=f"Fetched artifact #{artifact_id}",
        )
        return data

    def delete_artifact(self, artifact_id: int) -> bool:
        """
        Delete an artifact by ID.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#delete-an-artifact
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/actions/artifacts/{artifact_id}"
        )
        resp = self._delete(url)
        success = 200 <= resp.status_code < 300
        self._persist(
            {
                "artifact_id": artifact_id,
                "status_code": resp.status_code,
                "success": success,
            },
            filename=f"artifact_{artifact_id}_deleted.json",
            post_msg=f"Artifact #{artifact_id} deleted (status {resp.status_code}).",
        )
        return success

    def download_artifact(
        self,
        artifact_id: int,
        archive_format: str = "zip",
        output_path: str | Path | None = None,
    ) -> Path:
        """
        Download an artifact and save it locally.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#download-an-artifact
        """
        archive_format = archive_format.lower()
        if archive_format != "zip":
            raise ValueError(
                "GitHub currently supports only the 'zip' archive format. Please set archive_format as 'zip'."
            )
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/artifacts/{artifact_id}/{archive_format}"
        resp = self._get(url)
        target_path = (
            Path(output_path)
            if output_path is not None
            else self.output_dir / f"artifact_download_{artifact_id}.{archive_format}"
        )
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "wb") as artifact_file:
            artifact_file.write(resp.content)
        written_bytes = target_path.stat().st_size
        self._persist(
            {
                "artifact_id": artifact_id,
                "archive_format": archive_format,
                "output_path": str(target_path),
                "bytes": written_bytes,
            },
            filename=f"artifact_{artifact_id}_{archive_format}_download.json",
            post_msg=f"Artifact #{artifact_id} downloaded to {target_path} ({written_bytes} bytes).",
        )
        return target_path

    def list_action_runs_artifact(
        self, run_id: int, name: str | None = None, per_page: int = 30, page: int = 1
    ) -> dict[str, Any]:
        """
        List artifacts generated by a specific workflow run.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#list-workflow-run-artifacts
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/actions/runs/{run_id}/artifacts"
        )
        params: dict[str, Any] = {
            "per_page": per_page,
            "page": page,
        }
        if name is not None:
            params["name"] = name
        resp = self._get(url, params=params)
        data = resp.json()
        artifacts_count = len(data.get("artifacts", []))
        self._persist(
            data,
            filename=f"workflow_run_{run_id}_artifacts.json",
            post_msg=f"Fetched {artifacts_count} artifacts for workflow run #{run_id}.",
        )
        return data

    ## Cache
    def get_org_actions_cache_usage(self, org: str | None = None) -> dict[str, Any]:
        """
        Get cache usage for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#get-github-actions-cache-usage-for-an-organization
        """
        # default org_name is the repo_owner e.g. apache
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/cache/usage"
        resp = self._get(url)
        data = resp.json()
        usage_bytes = data.get("total_usage_in_bytes")
        self._persist(
            data,
            filename=f"org_{org_name}_cache_usage.json",
            post_msg=f"Org {org_name} cache usage: {usage_bytes} bytes.",
        )
        return data

    def list_org_actions_cache_usage_by_repo(
        self, org: str | None = None, per_page: int = 30, page: int = 1
    ) -> dict[str, Any]:
        """
        List cache usage for repositories within an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#list-repositories-with-github-actions-cache-usage-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/cache/usage-by-repository"
        params = {"per_page": per_page, "page": page}
        resp = self._get(url, params=params)
        data = resp.json()
        repo_count = len(data.get("repository_cache_usages", []))
        self._persist(
            data,
            filename=f"org_{org_name}_cache_usage_by_repo.json",
            post_msg=f"Fetched cache usage for {repo_count} repositories in org {org_name}.",
        )
        return data

    def get_repo_actions_cache_usage(self) -> dict[str, Any]:
        """
        Get cache usage for the current repository.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#get-github-actions-cache-usage-for-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/cache/usage"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename="repo_cache_usage.json",
            post_msg=(
                f"Repo {self.repo_owner}/{self.repo_name} cache usage: "
                f"{data.get('full_size_in_bytes')} bytes."
            ),
        )
        return data

    def list_repo_actions_caches(
        self,
        ref: str | None = None,
        key: str | None = None,
        sort: str | None = None,
        direction: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> dict[str, Any]:
        """
        List caches configured for the current repository.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#list-github-actions-caches-for-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/caches"
        params: dict[str, Any] = {
            "per_page": per_page,
            "page": page,
        }
        if key is not None:
            params["key"] = key
        if ref is not None:
            params["ref"] = ref
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        resp = self._get(url, params=params)
        data = resp.json()
        total_count = data.get("total_count", 0)
        self._persist(
            data,
            filename="repo_actions_caches.json",
            post_msg=f"Fetched {total_count} caches for repo {self.repo_owner}/{self.repo_name}.",
        )
        return data

    def delete_repo_actions_cache_with_key(
        self, key: str, ref: str | None = None
    ) -> bool:
        """
        Delete a cache entry by key
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#delete-github-actions-caches-for-a-repository-using-a-cache-key
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/caches"
        params: dict[str, Any] = {"key": key}
        if ref is not None:
            params["ref"] = ref
        resp = self._delete(url, params=params)
        success = 200 <= resp.status_code < 300
        self._persist(
            {
                "key": key,
                "ref": ref,
                "status_code": resp.status_code,
                "success": success,
            },
            filename="repo_actions_cache_delete_by_key.json",
            post_msg=f"Deleted cache with key={key} ref={ref}.",
        )
        return success

    def delete_repo_actions_cache_with_id(self, cache_id: int) -> bool:
        """
        Delete a cache entry by cache ID.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/cache?apiVersion=2022-11-28#delete-a-github-actions-cache-for-a-repository-using-a-cache-id
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/actions/caches/{cache_id}"
        resp = self._delete(url)
        success = 200 <= resp.status_code < 300
        self._persist(
            {
                "cache_id": cache_id,
                "status_code": resp.status_code,
                "success": success,
            },
            filename=f"repo_actions_cache_{cache_id}_deleted.json",
            post_msg=f"Deleted cache #{cache_id}.",
        )
        return success

    ## GitHub-Hosted runners
    def list_org_hosted_runners(
        self, org: str | None = None, per_page: int = 30, page: int = 1
    ) -> dict[str, Any]:
        """
        List GitHub-hosted runners for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#list-github-hosted-runners-for-an-organization
        """
        # default org_name is the repo_owner e.g. apache
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners"
        params = {"per_page": per_page, "page": page}
        resp = self._get(url, params=params)
        data = resp.json()
        total = data.get("total_count", 0)
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runners_page_{page}.json",
            post_msg=f"Fetched {total} hosted-runners for org {org_name}.",
        )
        return data

    def create_org_hosted_runner(
        self,
        name: str,
        image: dict[str, Any],
        size: str,
        runner_group_id: int,
        org: str | None = None,
        maximum_runners: int | None = None,
        enable_static_ip: bool | None = None,
        image_gen: bool | None = None,
    ) -> dict[str, Any]:
        """
        Create a GitHub-hosted runner for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#create-a-github-hosted-runner-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners"
        payload: dict[str, Any] = {
            "name": name,
            "image": image,
            "size": size,
            "runner_group_id": runner_group_id,
        }
        if maximum_runners is not None:
            payload["maximum_runners"] = maximum_runners
        if enable_static_ip is not None:
            payload["enable_static_ip"] = enable_static_ip
        if image_gen is not None:
            payload["image_gen"] = image_gen
        resp = self._post(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_created.json",
            post_msg=f"Created hosted-runner '{name}' in org {org_name}.",
        )
        return data

    def list_org_hosted_runner_custom_images(
        self, org: str | None = None
    ) -> dict[str, Any]:
        """
        List custom images for GitHub-hosted runners in an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#list-custom-images-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/images/custom"
        resp = self._get(url)
        data = resp.json()
        total = data.get("total_count", 0)
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_custom_images.json",
            post_msg=f"Fetched {total} hosted-runner custom images for org {org_name}.",
        )
        return data

    def get_org_hosted_runner_custom_image(
        self, image_definition_id: str, org: str | None = None
    ) -> dict[str, Any]:
        """
        Get a custom image definition for GitHub Actions hosted runners.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#get-a-custom-image-definition-for-github-actions-hosted-runners
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/images/custom/{image_definition_id}"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_custom_image_{image_definition_id}.json",
            post_msg=f"Fetched hosted-runner custom image {image_definition_id} for org {org_name}.",
        )
        return data

    def delete_org_hosted_runner_custom_image(
        self, image_definition_id: str, org: str | None = None
    ) -> bool:
        """
        Delete a custom image from the organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#delete-a-custom-image-from-the-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/images/custom/{image_definition_id}"
        resp = self._delete(url)
        success = 200 <= resp.status_code < 300
        self._persist(
            {
                "image_definition_id": image_definition_id,
                "status_code": resp.status_code,
                "success": success,
            },
            filename=f"org_{org_name}_hosted_runner_custom_image_{image_definition_id}_deleted.json",
            post_msg=f"Deleted hosted-runner custom image {image_definition_id} for org {org_name}.",
        )
        return success

    def list_org_hosted_runner_custom_image_versions(
        self, image_definition_id: str, org: str | None = None
    ) -> dict[str, Any]:
        """
        List image versions of a custom image for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#list-image-versions-of-a-custom-image-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/images/custom/{image_definition_id}/versions"
        resp = self._get(url)
        data = resp.json()
        total = data.get("total_count", 0)
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_custom_image_{image_definition_id}_versions.json",
            post_msg=(
                f"Fetched {total} hosted-runner custom image {image_definition_id} versions for org {org_name}."
            ),
        )
        return data

    def get_org_hosted_runner_custom_image_version(
        self, image_definition_id: str, version: str, org: str | None = None
    ) -> dict[str, Any]:
        """
        Get an image version of a custom image for GitHub Actions hosted runners.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#get-an-image-version-of-a-custom-image-for-github-actions-hosted-runners
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=(
                f"org_{org_name}_hosted_runner_custom_image_{image_definition_id}_version_{version}.json"
            ),
            post_msg=(
                f"Fetched hosted runner custom image {image_definition_id} version {version} for org {org_name}."
            ),
        )
        return data

    def delete_org_hosted_runner_custom_image_version(
        self, image_definition_id: str, version: str, org: str | None = None
    ) -> bool:
        """
        Delete an image version of a custom image from the organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#delete-an-image-version-of-custom-image-from-the-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/images/custom/{image_definition_id}/versions/{version}"
        resp = self._delete(url)
        success = 200 <= resp.status_code < 300
        self._persist(
            {
                "image_definition_id": image_definition_id,
                "version": version,
                "status_code": resp.status_code,
                "success": success,
            },
            filename=(
                f"org_{org_name}_hosted_runner_custom_image_{image_definition_id}_version_{version}_deleted.json"
            ),
            post_msg=(
                f"Deleted hosted runner custom image {image_definition_id} version {version} for org {org_name}."
            ),
        )
        return success

    def list_org_hosted_runner_github_owned_images(
        self, org: str | None = None
    ) -> dict[str, Any]:
        """
        Get the list of GitHub-owned images for GitHub-hosted runners in an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#get-github-owned-images-for-github-hosted-runners-in-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/images/github-owned"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_github_owned_images.json",
            post_msg=f"Fetched GitHub-owned hosted runner images for org {org_name}.",
        )
        return data

    def list_org_hosted_runner_partner_images(
        self, org: str | None = None
    ) -> dict[str, Any]:
        """
        Get the list of partner images for GitHub-hosted runners in an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#get-partner-images-for-github-hosted-runners-in-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/images/partner"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_partner_images.json",
            post_msg=f"Fetched partner hosted runner images for org {org_name}.",
        )
        return data

    def get_org_hosted_runner_limits(self, org: str | None = None) -> dict[str, Any]:
        """
        Get limits on GitHub-hosted runners for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#get-limits-on-github-hosted-runners-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/limits"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_limits.json",
            post_msg=f"Fetched hosted runner limits for org {org_name}.",
        )
        return data

    def get_org_hosted_runner_machine_sizes(
        self, org: str | None = None
    ) -> dict[str, Any]:
        """
        Get machine sizes for GitHub-hosted runners in an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#get-github-hosted-runners-machine-specs-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/machine-sizes"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_machine_sizes.json",
            post_msg=f"Fetched hosted runner machine sizes for org {org_name}.",
        )
        return data

    def list_org_hosted_runner_platforms(
        self, org: str | None = None
    ) -> dict[str, Any]:
        """
        Get the list of platforms for GitHub-hosted runners in an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#get-platforms-for-github-hosted-runners-in-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/platforms"
        resp = self._get(url)
        data = resp.json()
        total = data.get("total_count", 0)
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_platforms.json",
            post_msg=f"Fetched {total} hosted runner platforms for org {org_name}.",
        )
        return data

    def get_org_hosted_runner(
        self, hosted_runner_id: int, org: str | None = None
    ) -> dict[str, Any]:
        """
        Get a GitHub-hosted runner for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#get-a-github-hosted-runner-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/{hosted_runner_id}"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_{hosted_runner_id}.json",
            post_msg=f"Fetched hosted runner #{hosted_runner_id} for org {org_name}.",
        )
        return data

    def update_org_hosted_runner(
        self,
        hosted_runner_id: int,
        org: str | None = None,
        name: str | None = None,
        maximum_runners: int | None = None,
        enable_static_ip: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update a GitHub-hosted runner for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#update-a-github-hosted-runner-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/{hosted_runner_id}"
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if maximum_runners is not None:
            payload["maximum_runners"] = maximum_runners
        if enable_static_ip is not None:
            payload["enable_static_ip"] = enable_static_ip
        if not payload:
            raise ValueError(
                "At least one field must be provided to update a hosted runner."
            )
        resp = self._patch(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_{hosted_runner_id}_updated.json",
            post_msg=f"Updated hosted runner #{hosted_runner_id} for org {org_name}.",
        )
        return data

    def delete_org_hosted_runner(
        self, hosted_runner_id: int, org: str | None = None
    ) -> bool:
        """
        Delete a GitHub-hosted runner for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/hosted-runners?apiVersion=2022-11-28#delete-a-github-hosted-runner-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/hosted-runners/{hosted_runner_id}"
        resp = self._delete(url)
        success = 200 <= resp.status_code < 300
        # With body
        data = resp.json() if resp.content else {}
        self._persist(
            data,
            filename=f"org_{org_name}_hosted_runner_{hosted_runner_id}_deleted.json",
            post_msg=f"Deleted hosted runner #{hosted_runner_id} for org {org_name}, result {success}.",
        )
        return success

    ## OIDC
    def get_org_oidc_customization_sub(self, org: str | None = None) -> dict[str, Any]:
        """
        Get the customization template for an OIDC subject claim for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/oidc?apiVersion=2022-11-28#get-the-customization-template-for-an-oidc-subject-claim-for-an-organization
        """
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/oidc/customization/sub"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_oidc_customization_sub.json",
            post_msg=f"Fetched OIDC subject customization for org {org_name}.",
        )
        return data

    def set_org_oidc_customization_sub(
        self,
        use_default: bool,
        subject_claim_template: str | None = None,
        org: str | None = None,
    ) -> dict[str, Any]:
        """
        Set the customization template for an OIDC subject claim for an organization.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/oidc?apiVersion=2022-11-28#set-the-customization-template-for-an-oidc-subject-claim-for-an-organization
        """
        if not use_default and subject_claim_template is None:
            raise ValueError(
                "subject_claim_template is required when use_default is False."
            )
        org_name = org or self.repo_owner
        url = f"/orgs/{org_name}/actions/oidc/customization/sub"
        payload: dict[str, Any] = {"use_default": use_default}
        if subject_claim_template is not None:
            payload["subject_claim_template"] = subject_claim_template
        resp = self._put(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"org_{org_name}_oidc_customization_sub_set.json",
            post_msg=f"Updated OIDC subject customization for org {org_name}.",
        )
        return data

    def get_repo_oidc_customization_sub(self) -> dict[str, Any]:
        """
        Get the customization template for an OIDC subject claim for a repository.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/oidc?apiVersion=2022-11-28#get-the-customization-template-for-an-oidc-subject-claim-for-a-repository
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/actions/oidc/customization/sub"
        )
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename="repo_oidc_customization_sub.json",
            post_msg=(
                f"Fetched OIDC subject customization for repo {self.repo_owner}/{self.repo_name}."
            ),
        )
        return data

    def set_repo_oidc_customization_sub(
        self, use_default: bool, subject_claim_template: str | None = None
    ) -> dict[str, Any]:
        """
        Set the customization template for an OIDC subject claim for a repository.
        GitHub Docs:
        https://docs.github.com/en/rest/actions/oidc?apiVersion=2022-11-28#set-the-customization-template-for-an-oidc-subject-claim-for-a-repository
        """
        if not use_default and subject_claim_template is None:
            raise ValueError(
                "subject_claim_template is required when use_default is False."
            )
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/actions/oidc/customization/sub"
        )
        payload: dict[str, Any] = {"use_default": use_default}
        if subject_claim_template is not None:
            payload["subject_claim_template"] = subject_claim_template
        resp = self._put(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename="repo_oidc_customization_sub_set.json",
            post_msg=(
                f"Updated OIDC subject customization for repo {self.repo_owner}/{self.repo_name}."
            ),
        )
        return data

    ## TODO Permissions
    ## Link: https://docs.github.com/en/rest/actions/permissions?apiVersion=2022-11-28

    ## TODO Secrets
    ## Link: https://docs.github.com/en/rest/actions/secrets?apiVersion=2022-11-28

    ## TODO Self-hosted runner groups
    ## Link: https://docs.github.com/en/rest/actions/self-hosted-runner-groups?apiVersion=2022-11-28

    ## TODO Self-hosted runners
    ## Link: https://docs.github.com/en/rest/actions/self-hosted-runners?apiVersion=2022-11-28

    ## TODO Variables
    ## Link: https://docs.github.com/en/rest/actions/variables?apiVersion=2022-11-28

    ## TODO Workflow jobs
    ## Link: https://docs.github.com/en/rest/actions/workflow-jobs?apiVersion=2022-11-28

    ## TODO Workflow runs
    ## Link: https://docs.github.com/en/rest/actions/workflow-runs?apiVersion=2022-11-28

    ## TODO Workflows
    ## Link: https://docs.github.com/en/rest/actions/workflows?apiVersion=2022-11-28

    # Activity
    ## TODO Events
    ## Link: https://docs.github.com/en/rest/activity/events?apiVersion=2022-11-28

    ## TODO Feeds
    ## Link: https://docs.github.com/en/rest/activity/feeds?apiVersion=2022-11-28

    ## TODO Notifications
    ## Link: https://docs.github.com/en/rest/activity/notifications?apiVersion=2022-11-28

    ## TODO Starring
    ## Link: https://docs.github.com/en/rest/activity/starring?apiVersion=2022-11-28

    ## TODO Watching
    ## Link: https://docs.github.com/en/rest/activity/watching?apiVersion=2022-11-28

    # Apps
    ## TODO GitHub Apps
    ## Link: https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28

    ## TODO Installations
    ## Link: https://docs.github.com/en/rest/apps/installations?apiVersion=2022-11-28

    ## TODO Marketplace
    ## Link: https://docs.github.com/en/rest/apps/marketplace?apiVersion=2022-11-28

    ## TODO OAuth authorizations
    ## Link: https://docs.github.com/en/rest/apps/oauth-applications?apiVersion=2022-11-28

    ## TODO Webhooks
    ## Link: https://docs.github.com/en/rest/apps/webhooks?apiVersion=2022-11-28

    # Repository
    def get_repo_info(self) -> dict[str, Any]:
        """
        Get metadata of a specific repository.
        GitHub Docs:
        https://docs.github.com/en/rest/repos/repos?apiVersion=2022-11-28#get-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            # TODO configurable repo owner, repo name
            filename="repo_info.json",
            post_msg="Repository: {self.repo_owner}/{self.repo_name}",
        )
        return data

    # Issues
    def list_user_issues(
        self,
        filter: str = "assigned",
        state: str = "open",
        label_list: list[str] | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List issues assigned to the authenticated user across all visible repositories including owned repositories
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-issues-assigned-to-the-authenticated-user
        TODO full parameter/filter support
        TODO full media types support
        """
        url = "/issues"
        params = {
            "filter": filter,
            "state": state,
            "per_page": per_page,
            "page": page,
        }
        if label_list is not None:
            params["labels"] = ",".join(label_list)
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename="user_issues.json",
            post_msg=f"Fetched {len(data)} issues (filter={filter}, state={state})",
        )
        return data

    def list_repo_issues(
        self,
        milestone: list[str] | None = None,
        state: str = "open",
        assignee_list: list[str] | None = None,
        issue_type_list: list[str] | None = None,
        creator: str | None = None,
        mentioned: str | None = None,
        label_list: list[str] | None = None,
        sort: str | None = None,
        direction: str | None = None,
        since: str | None = None,
        per_page: int = 30,
        page: int = 1,
        output_filename: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List issues in the repository.
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#list-repository-issues
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues"
        params: dict[str, Any] = {"state": state, "per_page": per_page, "page": page}
        if milestone is not None:
            # like milestone in update_issue
            if len(milestone) == 0:
                params["milestone"] = "none"
            elif len(milestone) == 1:
                params["milestone"] = milestone[0]
            else:
                raise ValueError(
                    'Invalid `milestone` field in the param: expected an empty list [] or ["none"] to get issues without milestones '
                    'or a single-element list ["*"] to get issues with any milstone '
                    'or ["i"] an `integer` to get issues by `number` field.'
                )
        if assignee_list is not None:
            # Pass `none` for issues with no assigned user,
            # or `*` for issues assigned to any user
            if len(assignee_list) == 0:
                # Pass empty list
                params["assignee"] = "none"
            elif len(assignee_list) == 1:
                # only support single assignee query
                params["assignee"] = assignee_list[0]
            else:
                raise ValueError("Invalid `assignee` field in the param: TODO")
        if issue_type_list is not None:
            if len(issue_type_list) == 0:
                # Pass empty list
                params["type"] = "none"
            elif len(issue_type_list) == 1:
                params["type"] = issue_type_list[0]
            else:
                raise ValueError("Invalid `type` field in the param: TODO")
        if label_list is not None and label_list != []:
            params["labels"] = ",".join(label_list)
        if creator is not None:
            params["creator"] = creator
        if mentioned is not None:
            params["mentioned"] = mentioned
        # The `direction` parameter only takes effect when `sort` is explicitly specified.
        # Default behavior is sorted by `created` `desc`
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        elif direction is not None:
            logger.warning("⚠️ Ignoring direction since sort is not specified.")
        if since is not None:
            params["since"] = since
        resp = self._get(url, params=params)
        data = resp.json()
        # Allow callers to override the output name while retaining a descriptive default.
        filename = output_filename or f"repo_issues_page_{page}_per_{per_page}.json"
        self._persist(
            data,
            filename=filename,
            post_msg=f"Fetched {len(data)} issues (state={state})",
        )
        return data

    def get_issue(self, issue_number: int) -> dict[str, Any]:
        """
        Get a single issue.
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#get-an-issue
        :param issue_number: Issue or PR number
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"get_issue_{issue_number}.json",
            post_msg=f"Issue #{issue_number} fetched.",
        )
        return data

    def update_issue(
        self,
        issue_number: int,
        state: str,
        # Reason for the state change, choose from `completed`, `not_planned`, `duplicate`, `reopened`, `null`
        state_reason: str | None = None,
        title: str | None = None,
        body: str | None = None,
        # The number of the milestone, use `null` to remove the current milestone
        milestone: list[Any] | None = None,
        label_list: list[Any] | None = None,
        assignee_list: list[str] | None = None,
        # The name of the issue type to associate with this issue or use null to remove the current issue type
        issue_type_list: list[str] | None = None,
    ):
        """
        Update an issue.
        GitHub Docs:
        https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#update-an-issue
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}"

        # TODO check legal string of state
        payload: dict[str, Any] = {"state": state, "assignees": assignee_list}
        if state_reason is not None:
            # TODO check legal string of state_reason
            payload["state_reason"] = state_reason
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        if milestone is not None:
            # Interpret `milestone` as a wrapper list encoding different operations:
            # None → Do not modify (field omitted)
            # [] → Remove milestone (sends JSON null)
            # [v] → Set milestone (int or str)
            # _ → Raise error (more than one element)
            # Note: Python's `None` will correctly serialize to JSON `null` via `requests`.
            if len(milestone) == 0:
                payload["milestone"] = None
            elif len(milestone) == 1:
                payload["milestone"] = milestone[0]
            else:
                raise ValueError(
                    "Invalid `milestone` field in the payload: expected an empty list [] to remove existing milestone or a single-element list [m] to set m as the new milestone."
                )
        if label_list is not None:
            payload["labels"] = label_list
        if assignee_list is not None:
            payload["assignees"] = assignee_list
        if issue_type_list is not None:
            # Like milestone, use a wrapper list to translate the meaning of setting JSON `null`
            if len(issue_type_list) == 0:
                # []
                payload["type"] = None
            elif len(issue_type_list) == 1:
                payload["type"] = issue_type_list[0]
            else:
                raise ValueError(
                    "Invalid `type` field in the payload: expected an empty list [] to remove issue type or a single-element list [t] to set the issue type."
                )

        resp = self._patch(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"update_issue_{issue_number}.json",
            post_msg=f"Issue #{issue_number} updated (state={data.get('state', state)}).",
        )
        return data

    def lock_issue(self, issue_number: int, lock_reason: str) -> bool:
        """
        Lock an issue.
        GitHub Docs:
        https://docs.github.com/zh/rest/issues/issues?apiVersion=2022-11-28#lock-an-issue
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/lock"
        match lock_reason:
            case "off-topic" | "too heated" | "resolved" | "spam":
                logger.warning(f"⚠️ Try lock issue #{issue_number} by {lock_reason}")
            case _:
                raise ValueError(
                    "⚠️ The lock reason should be one of these: 'off-topic', 'too heated', 'resolved', 'spam' "
                )
        # It must be one of these reasons: `off-topic`, `too heated`, `resolved`, `spam`
        payload: dict[str, Any] = {"lock_reason": lock_reason}
        # status code 204 => locked, 403 => forbidden, 404 => resource not found, 410 => gone
        resp = self._put(url, json=payload)
        lock_result = resp.status_code == 204
        self._persist(
            lock_result,
            filename=f"lock_issue_{issue_number}.json",
            post_msg=f"Try lock Issue #{issue_number} (reason={lock_reason}). HTTP response status {lock_result}",
        )
        return lock_result

    def unlock_issue(self, issue_number: int) -> bool:
        """
        Unlock an issue.
        GitHub Docs:
        https://docs.github.com/zh/rest/issues/issues?apiVersion=2022-11-28#unlock-an-issue
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/lock"
        resp = self._delete(url)
        # status code 204 => locked, 403 => forbidden, 404 => Resource not found,
        unlock_result = resp.status_code == 204
        self._persist(
            unlock_result,
            filename=f"unlock_issue_{issue_number}.json",
            post_msg=f"Try unlock Issue #{issue_number}. HTTP response status {resp.status_code}",
        )
        return unlock_result

    # Pull requests
    # Pull requests are a type of issue. The common actions should be performed through the issues API endpoints
    ## Pull requests
    def list_repo_pulls(
        self,
        state: str = "open",
        head: str | None = None,
        base: str | None = None,
        sort: str | None = None,
        direction: str | None = None,
        per_page: int = 30,
        page: int = 1,
        output_filename: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        List pull requests in the repository.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls"
        params: dict[str, Any] = {"state": state, "per_page": per_page, "page": page}
        if head is not None:
            params["head"] = head
        if base is not None:
            params["base"] = base
        # The `direction` parameter only takes effect when `sort` is explicitly specified.
        # Default behavior is sorted by `created` `desc`
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        elif direction is not None:
            logger.warning("⚠️ Ignoring direction since sort is not specified.")
        resp = self._get(url, params=params)
        data = resp.json()
        # Mirror issue-list output behavior so consumers can control where results land.
        filename = output_filename or f"repo_pulls_page_{page}_per_{per_page}.json"
        self._persist(
            data,
            filename=filename,
            post_msg=f"Fetched {len(data)} pulls (state={state})",
        )
        return data

    def get_pull(self, pull_number: int):
        """
        Get a single pull request by number.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#get-a-pull-request
        :param pull_number: Pull request number (i.e., issue number of PR)
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}.json",
            post_msg=f"Fetched pull request #{pull_number}.",
        )
        return data

    def create_pull(
        self,
        title: str,  # required unless `issue` is specified
        head: str,
        head_repo,  # required for cross-repository prs
        base: str,
        body: str | None = None,
        draft: bool | None = None,
        issue_number: int | None = None,  # required unless `title` is specified
        maintainer_can_modify: bool | None = None,
    ) -> dict[str, Any]:
        """
        Create a pull request in the repository.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#create-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls"
        payload: dict[str, Any] = {"title": title, "head": head, "base": base}
        if body is not None:
            payload["body"] = body
        if maintainer_can_modify is not None:
            payload["maintainer_can_modify"] = maintainer_can_modify
        if draft is not None:
            payload["draft"] = draft
        # TODO Verify if `title` and `body` are respected when `issue` is provided.
        if issue_number is not None:
            payload["issue"] = issue_number
        resp = self._post(url, json=payload)
        data = resp.json()
        # Check use `id` or `number`
        new_pull_number = data.get("number", "unknown")
        self._persist(
            data,
            filename=f"pull_{new_pull_number}_created.json",
            post_msg=f"New pull request #{new_pull_number} created.",
        )
        return data

    def update_pull(
        self,
        pull_number: int,
        title: str | None = None,
        body: str | None = None,
        state: str | None = None,
        base: str | None = None,
        maintainer_can_modify: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#update-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}"
        payload: dict[str, Any] = {}
        if title is not None:
            payload["title"] = title
        if body is not None:
            payload["body"] = body
        # Can be `open`, `closed`
        if state is not None:
            payload["state"] = state
        if base is not None:
            payload["base"] = base
        if maintainer_can_modify is not None:
            payload["maintainer_can_modify"] = maintainer_can_modify
        resp = self._patch(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_updated.json",
            post_msg=f"Pull request #{pull_number} updated.",
        )
        return data

    def list_pull_commits(
        self, pull_number: int, per_page: int = 30, page: int = 1
    ) -> list[dict[str, Any]]:
        """
        List commits on a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-commits-on-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/commits"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_commits_page_{page}.json",
            post_msg=f"Fetched {len(data)} commits for pull #{pull_number}.",
        )
        return data

    def list_pull_files(
        self, pull_number: int, per_page: int = 30, page: int = 1
    ) -> list[dict[str, Any]]:
        """
        List files changed in a specified pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/files"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_files_page_{page}.json",
            post_msg=f"Fetched {len(data)} files for pull #{pull_number}.",
        )
        return data

    def is_pull_merged(self, pull_number: int) -> bool:
        """
        Check if a pull request has been merged.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#check-if-a-pull-request-has-been-merged
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/merge"
        resp = self._get(url)
        # If status code 204 => merged, 404 => not merged
        merge_result = resp.status_code == 204
        self._persist(
            merge_result,
            filename=f"pull_{pull_number}_merge_result.json",
            post_msg=f"Pull request #{pull_number} merged status: {merge_result}.",
        )
        return merge_result

    def merge_pull(
        self,
        pull_number: int,
        commit_title: str | None = None,
        commit_message: str | None = None,
        sha: str | None = None,
        merge_method: str | None = None,
    ):
        """
        Merge a pull request into the base branch. This endpoint triggers notifications.
        GitHub Docs:
        http://pulldocs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#merge-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/merge"
        payload: dict[str, Any] = {}
        if commit_title is not None:
            payload["commit_title"] = commit_title
        if commit_message is not None:
            payload["commit_message"] = commit_message
        if sha is not None:
            payload["sha"] = sha
        if merge_method is not None:
            match merge_method:
                case "merge" | "squash" | "rebase":
                    logger.warning(f"⚠️ Try merge #{pull_number} by {merge_method}")
                case _:
                    raise ValueError(
                        'The merge method to use should be one of: "merge, "squash", "rebase"'
                    )
            payload["merge_method"] = merge_method
        resp = self._put(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_try_merge.json",
            post_msg=f"Try merge pull request #{pull_number}.",
        )
        return data

    def update_pull_branch(
        self,
        pull_number: int,
        expected_head_sha: str | None = None,
    ):
        """
        Update the pull request branch by merging HEAD from base branch
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#update-a-pull-request-branch
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/update-branch"
        payload: dict[str, Any] = {}
        if expected_head_sha is not None:
            payload["expected_head_sha"] = expected_head_sha
        resp = self._put(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_update_branch.json",
            post_msg=f"Update pull request #{pull_number} branch.",
        )
        return data

    ## Review comments
    def list_repo_pull_review_comments(
        self,
        sort: str | None = None,
        direction: str | None = None,
        since: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List review comments across the repository.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#list-review-comments-in-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/comments"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        elif direction is not None:
            logger.warning("⚠️ Ignoring direction since sort is not specified.")
        if since is not None:
            params["since"] = since
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_review_comments_repo_{sort}_page_{page}.json",
            post_msg=f"Fetched {len(data)} repo pull review comments (sort={sort}).",
        )
        return data

    def get_pull_review_comment(self, comment_id: int) -> dict[str, Any]:
        """
        Get a review comment by ID.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#get-a-review-comment-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/comments/{comment_id}"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_review_comment_{comment_id}.json",
            post_msg=f"Fetched pull review comment #{comment_id}.",
        )
        return data

    def update_pull_review_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        """
        Update a pull request review comment.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#update-a-review-comment-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/comments/{comment_id}"
        payload: dict[str, Any] = {"body": body}
        resp = self._patch(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_review_comment_{comment_id}_updated.json",
            post_msg=f"Pull review comment #{comment_id} updated.",
        )
        return data

    def delete_pull_review_comment(self, comment_id: int) -> bool:
        """
        Delete a pull request review comment.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#delete-a-review-comment-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/comments/{comment_id}"
        resp = self._delete(url)
        delete_result = resp.status_code == 204
        self._persist(
            delete_result,
            filename=f"pull_review_comment_{comment_id}_deleted.json",
            post_msg=(
                f"Delete pull review comment #{comment_id}. "
                f"HTTP response status {resp.status_code}"
            ),
        )
        return delete_result

    def list_pull_review_comments(
        self,
        pull_number: int,
        sort: str | None = None,
        direction: str | None = None,
        since: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List all review comments for a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#list-review-comments-on-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/comments"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        elif direction is not None:
            logger.warning("⚠️ Ignoring direction since sort is not specified.")
        if since is not None:
            params["since"] = since
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_comments_{sort}_page_{page}.json",
            post_msg=f"Fetched {len(data)} review comments for pull #{pull_number}.",
        )
        return data

    def create_pull_review_comment(
        self,
        pull_number: int,
        body: str,
        commit_id: str | None = None,
        path: str | None = None,
        position: int | None = None,
        line: int | None = None,
        side: str | None = None,
        start_line: int | None = None,
        start_side: str | None = None,
        in_reply_to: int | None = None,
        subject_type: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a pull request review comment (or reply).
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#create-a-review-comment-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/comments"
        payload: dict[str, Any] = {"body": body}

        if in_reply_to is not None:
            # When specify `in_reply_to`, all parameters other than `body` are ignored
            payload["in_reply_to"] = in_reply_to
        else:
            if commit_id is None or path is None:
                raise ValueError(
                    "commit_id and path are required when creating a new review comment."
                )
            payload["commit_id"] = commit_id
            payload["path"] = path
            if subject_type is not None:
                payload["subject_type"] = subject_type

            if position is not None:
                # This parameter is closing down. Use `line` instead
                payload["position"] = position
            else:
                if line is None:
                    raise ValueError(
                        "Either position or line/side must be provided for review comments."
                    )
                if side is None:
                    raise ValueError("`side` is required when `line` is provided.")
                payload["line"] = line
                payload["side"] = side

                if start_line is not None:
                    if start_side is None:
                        raise ValueError(
                            "`start_side` is required when `start_line` is provided."
                        )
                    payload["start_line"] = start_line
                    payload["start_side"] = start_side
                elif start_side is not None:
                    raise ValueError(
                        "`start_line` must be set when `start_side` is provided."
                    )

        resp = self._post(url, json=payload)
        data = resp.json()
        comment_id = data.get("id", "unknown")
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_comment_{comment_id}_created.json",
            post_msg=f"Pull review comment #{comment_id} for pull #{pull_number} created.",
        )
        return data

    def create_reply_pull_review_comment(
        self, pull_number: int, comment_id: int, body: str
    ) -> dict[str, Any]:
        """
        Create a reply to a review comment.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/comments?apiVersion=2022-11-28#create-a-reply-for-a-review-comment
        """
        # Replies to replies are not supported.
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/comments/{comment_id}/replies"
        payload: dict[str, Any] = {"body": body}
        resp = self._post(url, json=payload)
        data = resp.json()
        reply_id = data.get("id", "unknown")
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_comment_{comment_id}_replied_{reply_id}.json",
            post_msg=f"Pull reply to review comment #{comment_id}, reply_id #{reply_id}, for pull #{pull_number} created.",
        )
        return data

    ## Review requests
    def list_pull_requested_reviewers(
        self, pull_number: int, output_filename: str | None = None
    ) -> dict[str, Any]:
        """
        List requested reviewers for a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/review-requests?apiVersion=2022-11-28#list-requested-reviewers-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/requested_reviewers"
        resp = self._get(url)
        data = resp.json()
        filename = output_filename or f"pull_{pull_number}_requested_reviewers.json"
        self._persist(
            data,
            filename=filename,
            post_msg=f"Fetched requested reviewers for pull #{pull_number}.",
        )
        return data

    def request_pull_reviewers(
        self,
        pull_number: int,
        reviewers: list[str] | None = None,
        team_reviewers: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Request reviewers for a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/review-requests?apiVersion=2022-11-28#request-reviewers-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/requested_reviewers"
        payload: dict[str, Any] = {}
        if reviewers:
            payload["reviewers"] = reviewers
        if team_reviewers:
            payload["team_reviewers"] = team_reviewers
        if not payload:
            raise ValueError(
                "At least one reviewer or team_reviewer must be specified."
            )
        resp = self._post(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_requested_reviewers_added.json",
            post_msg=f"Requested reviewers for pull #{pull_number}.",
        )
        return data

    def remove_pull_reviewers(
        self,
        pull_number: int,
        reviewers: list[str] | None = None,
        team_reviewers: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Remove requested reviewers from a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/review-requests?apiVersion=2022-11-28#remove-requested-reviewers-from-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/requested_reviewers"
        payload: dict[str, Any] = {}
        ## Not sure if None is ok, marked as required in the doc
        # if reviewers is None:
        #     raise ValueError("Reviewers list should not be empty.")
        # payload["reviewers"] = reviewers
        if reviewers:
            payload["reviewers"] = reviewers
        if team_reviewers:
            payload["team_reviewers"] = team_reviewers
        resp = self._delete(url, json=payload)
        data = resp.json() if resp.content else {}
        self._persist(
            data,
            filename=f"pull_{pull_number}_requested_reviewers_removed.json",
            post_msg=f"Removed requested reviewers {reviewers}, {team_reviewers} for pull #{pull_number}.",
        )
        return data

    ## Review
    def list_pull_reviews(
        self, pull_number: int, per_page: int = 30, page: int = 1
    ) -> list[dict[str, Any]]:
        """
        List reviews for a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#list-reviews-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/reviews"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_reviews_page_{page}.json",
            post_msg=f"Fetched {len(data)} reviews for pull #{pull_number}.",
        )
        return data

    def create_pull_review(
        self,
        pull_number: int,
        commit_id: str | None = None,
        body: str | None = None,
        event: str | None = None,
        comments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Create a pull request review.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#create-a-review-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/reviews"
        payload: dict[str, Any] = {}
        if body is not None:
            payload["body"] = body
        if event is not None:
            payload["event"] = event
        # The comments properties should follow the docs
        if comments is not None:
            payload["comments"] = comments
        if commit_id is not None:
            payload["commit_id"] = commit_id
        if body is None and event is None and comments is None:
            raise ValueError("Must specify at least one of body, event, or comments.")
        resp = self._post(url, json=payload)
        data = resp.json()
        review_id = data.get("id", "unknown")
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_{review_id}_created.json",
            post_msg=f"Created review #{review_id} for pull #{pull_number}.",
        )
        return data

    def get_pull_review(self, pull_number: int, review_id: int) -> dict[str, Any]:
        """
        Get a single review for a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#get-a-review-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/reviews/{review_id}"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_{review_id}.json",
            post_msg=f"Fetched pull #{pull_number} review #{review_id}.",
        )
        return data

    def update_pull_review(
        self, pull_number: int, review_id: int, body: str
    ) -> dict[str, Any]:
        """
        Update a pull request review.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#update-a-review-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/reviews/{review_id}"
        payload: dict[str, Any] = {"body": body}
        resp = self._put(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_{review_id}_updated.json",
            post_msg=f"Updated review #{review_id} for pull #{pull_number}.",
        )
        return data

    def delete_pull_pending_review(self, pull_number: int, review_id: int):
        """
        Delete a pending review for a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#delete-a-pending-review-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/reviews/{review_id}"
        resp = self._delete(url)
        delete_result = resp.status_code in {200, 204}
        # With body
        data = resp.json() if resp.content else {}
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_{review_id}_deleted.json",
            post_msg=(
                f"Delete review #{review_id} for pull #{pull_number}, result: {delete_result}. "
                f"HTTP response status {resp.status_code}"
            ),
        )
        return data

    def list_pull_review_comments_for_review(
        self, pull_number: int, review_id: int, per_page: int = 30, page: int = 1
    ) -> list[dict[str, Any]]:
        """
        List comments for a pull request review.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#list-comments-for-a-pull-request-review
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/reviews/{review_id}/comments"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_{review_id}_comments_page_{page}.json",
            post_msg=(
                f"Fetched {len(data)} comments for review #{review_id} on pull #{pull_number}."
            ),
        )
        return data

    def dismiss_pull_review(
        self,
        pull_number: int,
        review_id: int,
        message: str,
        event: str,
    ) -> dict[str, Any]:
        """
        Dismiss a review for a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#dismiss-a-review-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/reviews/{review_id}/dismissals"
        payload: dict[str, Any] = {"message": message}
        if event != "DISMISS":
            raise ValueError('event only accept "DISMISS"')
        payload["event"] = "DISMISS"
        resp = self._put(url, json=payload)
        dismiss_result = resp.status_code in {200, 204}
        # With body
        data = resp.json() if resp.content else {}
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_{review_id}_dismissed.json, result {dismiss_result}",
            post_msg=f"Dismissed review #{review_id} for pull #{pull_number}.",
        )
        return data

    def submit_pull_review(
        self,
        pull_number: int,
        review_id: int,
        event: str,
        body: str | None = None,
    ) -> dict[str, Any]:
        """
        Submit a review for a pull request.
        GitHub Docs:
        https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#submit-a-review-for-a-pull-request
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/pulls/{pull_number}/reviews/{review_id}/events"
        match event:
            case "APPROVE" | "REQUEST_CHANGES" | "COMMENT":
                logger.warning(
                    f"⚠️ Try submit pull #{pull_number} review_id {review_id} as {event}"
                )
            case _:
                raise ValueError("event must be APPROVE, REQUEST_CHANGES, or COMMENT")
        payload: dict[str, Any] = {"event": event}
        if body is not None:
            payload["body"] = body
        resp = self._post(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"pull_{pull_number}_review_{review_id}_submitted.json",
            post_msg=f"Submitted review #{review_id} for pull #{pull_number} with event {event}.",
        )
        return data

    # Markdown
    def render_markdown(
        self,
        text: str,
        mode: str = "markdown",
        context: str | None = None,
        output_filename: str | None = None,
    ):
        """
        Render a markdown document
        GitHub Docs:
        https://docs.github.com/zh/rest/markdown/markdown?apiVersion=2022-11-28#render-a-markdown-document
        """
        url = "/markdown"
        payload = {"text": text, "mode": mode}
        if context is not None:
            # use when use `gfm` mode
            if mode == "gfm":
                # context like `octo-org/octo-repo` to convert the `#42` to issue 42 link
                payload["context"] = context
            elif mode == "markdown":
                logger.info(
                    "Try to render a markdown with `markdown` mode. `context` setting does not work."
                )
        resp = self._post(url, json=payload)
        rendered = resp.text
        # Always persist
        if output_filename is None:
            filename = f"markdown_rendered_{mode}.html"
        else:
            filename = output_filename
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        logger.info(f"Rendered markdown saved -> {output_path}")
        return rendered

    def render_markdown_raw(
        self,
        text: str,
        output_filename: str | None = None,
    ):
        """
        Render a markdown document in raw media
        GitHub Docs:
        https://docs.github.com/en/rest/markdown/markdown?apiVersion=2022-11-28#render-a-markdown-document-in-raw-mode
        TODO official doc is not good
        """
        url = "/markdown/raw"
        # using `text/plain` ir `text/x-markdown`
        headers: dict[str, str] = {
            "Content-Type": SupportMediaTypes.TEXT_PLAIN.value,
            "Accept": SupportMediaTypes.TEXT_HTML.value,
        }
        resp = self._post(url, headers=headers, data=text.encode("utf-8"), if_json=False)
        rendered = resp.text
        # Always persist
        if output_filename is None:
            filename = "markdown_rendered_raw.html"
        else:
            filename = output_filename
        output_path = self.output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(rendered)
        logger.info(f"Rendered markdown raw saved -> {output_path}")
        return rendered

    # Comments
    def list_repo_issue_comments(
        self,
        sort: str | None = None,
        direction: str | None = None,
        since: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List issue comments for a repository
        GitHub Docs:
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#list-issue-comments-for-a-repository
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/comments"
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        # The `direction` parameter only takes effect when `sort` is explicitly specified.
        # Default behavior is sorted by `created` `desc`
        if sort is not None:
            params["sort"] = sort
            if direction is not None:
                params["direction"] = direction
        elif direction is not None:
            logger.warning("⚠️ Ignoring direction since sort is not specified.")
        if since is not None:
            params["since"] = since
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"repo_issue_comments_{sort}_page_{page}.json",
            post_msg=f"Fetched {len(data)} repo issue comments (sort={sort}).",
        )
        return data

    def list_issue_comments(
        self,
        issue_number: int,
        since: str | None = None,
        per_page: int = 30,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """
        List issue comments with specific `issue_number` (Every pr is an issue, but not every issue is a pr)
        GitHub Docs:
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#list-issue-comments
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/comments"
        )
        params: dict[str, Any] = {"per_page": per_page, "page": page}
        if since is not None:
            params["since"] = since
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"issue_{issue_number}_comments_page_{page}.json",
            post_msg=f"Fetched {len(data)} comments for issue #{issue_number}.",
        )
        return data

    def create_single_issue_comment(
        self, issue_number: int, body: str
    ) -> dict[str, Any]:
        """
        Create an issue comment
        GitHub Docs:
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#create-an-issue-comment
        """
        url = (
            f"/repos/{self.repo_owner}/{self.repo_name}/issues/{issue_number}/comments"
        )
        payload: dict[str, Any] = {"body": body}
        resp = self._post(url, json=payload)
        data = resp.json()
        new_comment_id = data.get("id", "unknown")
        self._persist(
            data,
            filename=f"issue_comment_{new_comment_id}_created.json",
            post_msg=f"Issue comment #{new_comment_id} for issue #{issue_number} created.",
        )
        return data

    def get_single_issue_comment(
        self,
        comment_id: int,
    ) -> dict[str, Any]:
        """
        Get an issue comment with specific `comment_id`
        GitHub Docs:
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#get-an-issue-comment
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/comments/{comment_id}"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename=f"issue_comment_{comment_id}_readed.json",
            post_msg=f"Issue comment #{comment_id} fetched.",
        )
        return data

    def update_single_issue_comment(self, comment_id: int, body: str) -> dict[str, Any]:
        """
        Update an issue comment
        GitHub Docs:
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#update-an-issue-comment
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/comments/{comment_id}"
        payload: dict[str, Any] = {"body": body}
        resp = self._patch(url, json=payload)
        data = resp.json()
        self._persist(
            data,
            filename=f"issue_comment_{comment_id}_updated.json",
            post_msg=f"Issue comment #{comment_id} updated.",
        )
        return data

    def delete_single_issue_comment(
        self,
        comment_id: int,
    ) -> bool:
        """
        Delete an issue comment
        GitHub Docs:
        https://docs.github.com/en/rest/issues/comments?apiVersion=2022-11-28#delete-an-issue-comment
        """
        url = f"/repos/{self.repo_owner}/{self.repo_name}/issues/comments/{comment_id}"
        resp = self._delete(url)
        delete_result = resp.status_code == 204
        self._persist(
            delete_result,
            filename=f"issue_comment_{comment_id}_deleted.json",
            post_msg=f"Delete issue comment #{comment_id}. HTTP response status {resp.status_code}",
        )
        return delete_result

    # Meta
    def get_zen(self) -> str:
        """
        Get the Zen of GitHub.
        GitHub Docs:
        https://docs.github.com/en/rest/meta/meta?apiVersion=2022-11-28#get-the-zen-of-github
        """
        url = "/zen"
        resp = self._get(url)
        zen_text = resp.text.strip()
        self._persist(
            {"zen": zen_text},
            filename="github_zen.json",
            post_msg=f'Fetched GitHub Zen text:\n"{zen_text}"',
        )
        return zen_text

    def get_octocat(self, speech_str: str | None = None) -> str:
        """
        Get the Octocat of GitHub
        GitHub Docs:
        https://docs.github.com/en/rest/meta/meta?apiVersion=2022-11-28#get-octocat
        """
        url = "/octocat"
        params: dict[str, Any] = {}
        if speech_str is not None:
            params["s"] = speech_str
        resp = self._get(url, params=params)
        octocat = resp.text
        self._persist(
            {"speech": speech_str, "octocat": octocat},
            filename="github_octocat.json",
            post_msg=f"🐙 Octocat fetched\n{octocat}",
        )
        return octocat

    def get_api_root(self) -> dict[str, Any]:
        """
        Get GitHub API root hypermedia links to top-level API resources.
        GitHub Docs:
        https://docs.github.com/en/rest/meta/meta?apiVersion=2022-11-28#get-apiname-meta-information
        """
        url = "/"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename="github_api_root.json",
            post_msg=f"Fetched GitHub API root with {len(data)} keys.",
        )
        return data

    def get_github_meta(self) -> dict[str, Any]:
        """
        Get meta information about GitHub
        GitHub Docs:
        https://docs.github.com/en/rest/meta/meta?apiVersion=2022-11-28#get-github-meta-information
        """
        url = "/meta"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename="github_meta.json",
            post_msg=f"Fetched GitHub API metadata with {len(data)} keys.",
        )
        return data

    def get_api_versions(self) -> list[str]:
        """
        Get all supported GitHub API versions
        GitHub Docs:
        https://docs.github.com/en/rest/meta/meta?apiVersion=2022-11-28#get-all-api-versions
        """
        url = "/versions"
        resp = self._get(url)
        data = resp.json()
        self._persist(
            data,
            filename="github_api_versions.json",
            post_msg=f"List all supported GitHub API versions:\n {data}",
        )
        return data

    # User
    def get_authenticated_user(self) -> dict[str, Any]:
        """
        Get the currently authenticated user's profile.
        GitHub Docs:
        https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-the-authenticated-user
        """
        url = "/user"
        resp = self._get(url)
        data = resp.json()
        # get user_login and user_id
        user_login = data.get("login", "UNKNOWN")
        user_id = data.get("id", "UNKNOWN")
        self._persist(
            data,
            filename=f"auth_user_{user_id}_{user_login}.json",
            post_msg="Fetched authenticated user info.",
        )
        return data

    def update_authenticated_user(
        self,
        name: str | None,
        email: str | None,
        blog: str | None,
        twitter_username: str | None,
        company: str | None,
        location: str | None,
        hireable: bool | None,
        bio: str | None,
    ) -> dict[str, Any]:
        """
        Update the authenticated user's profile
        Note: the changed `email` will not be desplayed on the public profile if your proivacy settings are still enforced.
        GitHub Docs:
        https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#update-the-authenticated-user
        """
        url = "/user"
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if email is not None:
            payload["email"] = email
        if blog is not None:
            payload["blog"] = blog
        if twitter_username is not None:
            payload["twitter_username"] = twitter_username
        if company is not None:
            payload["company"] = company
        if location is not None:
            payload["location"] = location
        if hireable is not None:
            payload["hireable"] = hireable
        resp = self._patch(url, json=payload)
        data = resp.json()
        # get user_login and user_id
        user_login = data.get("login", "UNKNOWN")
        user_id = data.get("id", "UNKNOWN")
        self._persist(
            data,
            filename=f"auth_user_{user_id}_{user_login}_updated.json",
            post_msg=f"Updated authenticated user info.",
        )
        return data

    def get_user_with_userid(self, userid: str) -> dict[str, Any]:
        """
        Get someone's public information with their user id.
        GitHub Docs:
        https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-a-user-using-their-id
        """
        url = f"/user/{userid}"
        resp = self._get(url)
        data = resp.json()
        # get user_login and user_id
        user_login = data.get("login", "UNKNOWN")
        user_id = data.get("id", "UNKNOWN")
        user_login = data.get("login", "UNKNOWN")
        self._persist(
            data,
            filename=f"user_{user_id}_{user_login}_by_userid.json",
            post_msg=f"Fetched user info for {user_id}",
        )
        return data

    def list_users(
        self,
        since: int | None,
        per_page: int = 30,
    ) -> list[dict[str, Any]]:
        """
        List all users in the order they signed up including personal user accounts and organization accounts.
        GitHub Docs:
        https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#list-users
        """
        url = "/users"
        params: dict[str, Any] = {"per_page": per_page}
        if since is not None:
            params["since"] = since
        resp = self._get(url, params=params)
        data = resp.json()
        self._persist(
            data,
            filename=f"users.json",
            post_msg=f"Fetched {len(data)} users.",
        )
        return data

    def get_user_with_username(self, username: str) -> dict[str, Any]:
        """
        Get someone's public information with their username.
        Note:
        If you are requesting information about an Enterprise Managed User, or a GitHub App bot that is installed in an organization that uses Enterprise Managed Users, you must be authenticate.
        GitHub Docs:
        https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-a-user
        """
        url = f"/users/{username}"
        resp = self._get(url)
        data = resp.json()
        # get user_login and user_id
        user_login = data.get("login", "UNKNOWN")
        user_id = data.get("id", "UNKNOWN")
        self._persist(
            data,
            filename=f"user_{user_id}_{user_login}_by_username.json",
            post_msg=f"Fetched user info for {username}.",
        )
        return data

    # TODO add get_user_contextual
    # https://docs.github.com/en/rest/users/users?apiVersion=2022-11-28#get-contextual-information-for-a-user
