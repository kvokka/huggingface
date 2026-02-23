from __future__ import annotations

import argparse
import os
from pathlib import Path

from scripts.hf_client import HfClient


def parse_bool(value: str) -> bool:
    v = value.strip().lower()
    if v in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if v in {"0", "false", "f", "no", "n", "off", ""}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def build_ui_url(repo_id: str, repo_type: str) -> str:
    if repo_type == "space":
        return f"https://huggingface.co/spaces/{repo_id}"
    if repo_type == "dataset":
        return f"https://huggingface.co/datasets/{repo_id}"
    if repo_type == "model":
        return f"https://huggingface.co/{repo_id}"
    raise ValueError(f"Unsupported repo_type: {repo_type}")


def normalize_repo_type(repo_type: str) -> str:
    rt = repo_type.strip().lower()
    if rt not in {"space", "model", "dataset"}:
        raise ValueError("repo_type must be one of: space, model, dataset")
    return rt


def compute_repo_id(
    *,
    huggingface_repo: str,
    github_repo: str,
    token_owner: str,
) -> str:
    if huggingface_repo == "same_with_github_repo":
        huggingface_repo = github_repo

    if not huggingface_repo or huggingface_repo.strip() == "":
        raise ValueError("huggingface_repo must not be empty")

    if "/" in huggingface_repo:
        return huggingface_repo
    return f"{token_owner}/{huggingface_repo}"


def compute_proxy_repo_id(*, target_repo_id: str, suffix: str) -> str:
    if "/" not in target_repo_id:
        raise ValueError("target_repo_id must be in the form owner/name")
    owner, name = target_repo_id.split("/", 1)
    if not suffix:
        raise ValueError("proxy_space_suffix must not be empty")
    return f"{owner}/{name}{suffix}"


def compute_default_space_runtime_url(*, repo_id: str) -> str:
    if "/" not in repo_id:
        raise ValueError("repo_id must be in the form owner/name")
    owner, name = repo_id.split("/", 1)
    return f"https://{owner}-{name}.hf.space"


def write_outputs(outputs: dict[str, str]) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        raise RuntimeError("GITHUB_OUTPUT is not set")
    with open(output_path, "a", encoding="utf-8") as f:
        for k, v in outputs.items():
            if "\n" in v:
                raise ValueError(f"Output {k} contains newline")
            f.write(f"{k}={v}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy to Hugging Face")
    parser.add_argument("--huggingface-repo", required=True)
    parser.add_argument("--hf-token", required=True)
    parser.add_argument("--repo-type", default="space")
    parser.add_argument("--space-sdk", default="gradio")
    parser.add_argument("--private", default="false")
    parser.add_argument("--source-dir", default=".")
    parser.add_argument("--commit-message", default="sync: deploy from GitHub Actions")
    parser.add_argument("--create-proxy", default="false")
    parser.add_argument("--proxy-space-suffix", default="-proxy")
    parser.add_argument("--proxy-hf-token", default="")
    parser.add_argument("--proxy-target-url", default="")
    parser.add_argument("--proxy-allow-origins", default="*")

    args = parser.parse_args()

    repo_type = normalize_repo_type(args.repo_type)
    private = parse_bool(args.private)
    create_proxy = parse_bool(args.create_proxy)

    if create_proxy and repo_type != "space":
        raise ValueError("create_proxy=true requires repo_type=space")

    github_repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not github_repo:
        raise RuntimeError("GITHUB_REPOSITORY is not set")

    source_dir = Path(args.source_dir)
    if not source_dir.is_dir():
        raise ValueError(f"source_dir does not exist or is not a directory: {source_dir}")

    client = HfClient(token=args.hf_token)
    owner = client.whoami()

    repo_id = compute_repo_id(
        huggingface_repo=args.huggingface_repo,
        github_repo=github_repo,
        token_owner=owner,
    )

    space_sdk = args.space_sdk if repo_type == "space" else None

    client.ensure_repo(
        repo_id=repo_id,
        repo_type=repo_type,
        private=private,
        space_sdk=space_sdk,
    )

    client.upload_folder(
        folder_path=source_dir,
        repo_id=repo_id,
        repo_type=repo_type,
        commit_message=args.commit_message,
        ignore_patterns=[".git/**", "**/.git/**", "**/__pycache__/**"],
    )

    repo_url = build_ui_url(repo_id, repo_type)
    space_url = repo_url if repo_type == "space" else ""

    proxy_enabled = "false"
    proxy_repo_id = ""
    proxy_url = ""

    if create_proxy:
        proxy_enabled = "true"
        proxy_repo_id = compute_proxy_repo_id(
            target_repo_id=repo_id,
            suffix=args.proxy_space_suffix,
        )
        upstream_url = args.proxy_target_url.strip() or compute_default_space_runtime_url(
            repo_id=repo_id
        )

        proxy_token = args.proxy_hf_token.strip() or args.hf_token
        if not proxy_token:
            raise ValueError("proxy_hf_token fallback produced empty token")

        client.ensure_repo(
            repo_id=proxy_repo_id,
            repo_type="space",
            private=False,
            space_sdk="docker",
        )
        client.set_space_variable(repo_id=proxy_repo_id, key="TARGET_URL", value=upstream_url)
        client.set_space_variable(
            repo_id=proxy_repo_id, key="ALLOW_ORIGINS", value=args.proxy_allow_origins
        )
        client.set_space_secret(repo_id=proxy_repo_id, key="HF_TOKEN", value=proxy_token)

        proxy_template = Path(__file__).parent / "proxy_template"
        client.upload_folder(
            folder_path=proxy_template,
            repo_id=proxy_repo_id,
            repo_type="space",
            commit_message="sync: proxy template",
            ignore_patterns=[".git/**", "**/.git/**", "**/__pycache__/**"],
        )
        proxy_url = build_ui_url(proxy_repo_id, "space")

    write_outputs(
        {
            "repo_id": repo_id,
            "repo_url": repo_url,
            "space_url": space_url,
            "proxy_enabled": proxy_enabled,
            "proxy_repo_id": proxy_repo_id,
            "proxy_url": proxy_url,
        }
    )


if __name__ == "__main__":
    main()
