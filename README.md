# Deploy to Hugging Face (Spaces/Models/Datasets)

[![Build Status](https://img.shields.io/github/actions/workflow/status/kvokka/huggingface/ci.yml)](https://github.com/kvokka/huggingface/actions)
[![Integration (Hugging Face)](https://img.shields.io/github/actions/workflow/status/kvokka/huggingface/integration-hf.yml?label=integration)](https://github.com/kvokka/huggingface/actions/workflows/integration-hf.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/kvokka/huggingface)](https://github.com/kvokka/huggingface/releases/latest)
[![GitHub stars](https://img.shields.io/github/stars/kvokka/huggingface)](https://github.com/kvokka/huggingface/stargazers)
[![Sponsor](https://img.shields.io/badge/Sponsor-%E2%9D%A4-pink?logo=github-sponsors)](https://github.com/sponsors/kvokka)

This is a **root-level composite GitHub Action** that syncs a local folder to a Hugging Face repo:

- `repo_type=space`
- `repo_type=model`
- `repo_type=dataset`

It also supports an optional (default **OFF**) feature to create a **public proxy Space** that forwards requests to a **private Space API**.

## Quick start

```yaml
name: Deploy to Hugging Face

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6

      - uses: kvokka/huggingface@v0
        with:
          hf_token: ${{ secrets.HF_TOKEN }}
          repo_type: space
          huggingface_repo: "my-username/my-space"
          source_dir: .
```

## Inputs

| Name | Required | Default | Notes |
|---|---:|---|---|
| `huggingface_repo` | no | `same_with_github_repo` | Accepts `owner/name` or just `name` (will use token owner). |
| `hf_token` | yes |  | Hugging Face token with write access. |
| `repo_type` | no | `space` | `space` \| `model` \| `dataset`. |
| `space_sdk` | no | `gradio` | Only used when creating a **new** Space. |
| `private` | no | `false` | Only applies on creation. |
| `source_dir` | no | `.` | Folder uploaded to Hugging Face. |
| `commit_message` | no | `sync: deploy from GitHub Actions` | Commit message for the upload commit. |
| `create_proxy` | no | `false` | If `true`, create/update a public proxy Space for the target Space. |
| `proxy_space_suffix` | no | `-proxy` | Proxy Space name suffix. |
| `proxy_hf_token` | no | empty | Recommended: a **dedicated** token for proxy upstream calls. Falls back to `hf_token`. |
| `proxy_target_url` | no | empty | If empty, computed as `https://{owner}-{space}.hf.space`. |
| `proxy_allow_origins` | no | `*` | `*` or a comma-separated list of allowed origins. |

## Outputs

| Name | Description |
|---|---|
| `repo_id` | Resolved Hugging Face repo id (`owner/name`). |
| `repo_url` | Hugging Face UI URL for the repo. |
| `space_url` | Hugging Face UI URL for the Space (empty for non-space). |
| `proxy_enabled` | `true`/`false`. |
| `proxy_repo_id` | Proxy repo id (empty if disabled). |
| `proxy_url` | Proxy Space UI URL (empty if disabled). |

## Optional public proxy Space

This feature is intended for cases where:

- your **target Space is private**, and
- you want a **public** Space endpoint that forwards requests to the private API.

Example:

```yaml
- uses: kvokka/huggingface@v0
  with:
    hf_token: ${{ secrets.HF_TOKEN }}
    huggingface_repo: "my-username/my-private-space"
    repo_type: space
    private: true
    source_dir: .

    create_proxy: true
    proxy_hf_token: ${{ secrets.PROXY_HF_TOKEN }}
    proxy_allow_origins: "https://myapp.example"
```

### Security guidance

- Prefer a dedicated `proxy_hf_token` over reusing `hf_token`.
- Never print tokens in logs; this repo’s scripts avoid printing token values.

## Limitations

Please keep in mind the quota of huggingface free API:

```plain
429 Too Many Requests: you have reached your 'api' rate limit.
Retry after 188 seconds (977/1000 requests remaining in current 300s window).
Url: https://huggingface.co/api/repos/create.
You have exceeded the rate limit for space creation (20 per day). You can retry this action in 1 day.
```

## Integration tests + cleanup

This repo includes real Hugging Face integration workflows:

- `.github/workflows/integration-hf.yml` invokes the action via `uses: ./`, verifies outputs and deployed resources, and always tears down created repos.
- `.github/workflows/janitor.yml` is a scheduled cleanup that deletes stale repos whose name starts with `hf-space-action-test-`.

## Dependencies

Runtime:

- `huggingface_hub`

Dev:

- `pytest`
- `ruff`
- `ty`
- `fastapi`, `httpx` (for proxy template type stubs)

## Development

### Prerequisites

- Python 3.14+
- A [Hugging Face account](https://huggingface.co) with a write-access token (for integration tests)

### Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### Running locally

```bash
ruff check .                  # lint (Python)
ty check                      # type check (Python)
hadolint scripts/proxy_template/Dockerfile  # lint (Dockerfile)
rumdl check --no-exclude .    # lint (Markdown)
PYTHONPATH=. pytest            # unit tests
```

### Secrets and environment variables

| Variable | Where | Purpose |
|---|---|---|
| `HF_TOKEN` | GitHub repo secret | Hugging Face write token. Used by integration tests, janitor, and the action itself. |
| `PROXY_HF_TOKEN` *(optional)* | GitHub repo secret | Dedicated token for proxy upstream calls. Falls back to `HF_TOKEN` if absent. |

To run the deploy script locally (outside the action), export `HF_TOKEN` and `GITHUB_REPOSITORY`:

```bash
export HF_TOKEN="hf_..."
export GITHUB_REPOSITORY="owner/repo"
export GITHUB_OUTPUT=$(mktemp)
PYTHONPATH=. python -m scripts.deploy \
  --huggingface-repo owner/test-space \
  --hf-token "${HF_TOKEN}" \
  --repo-type space \
  --space-sdk gradio \
  --private false \
  --source-dir . \
  --commit-message "local test" \
  --create-proxy false \
  --proxy-space-suffix -proxy \
  --proxy-hf-token "" \
  --proxy-target-url "" \
  --proxy-allow-origins "*"
```

### Creating the `HF_TOKEN` secret

1. Go to [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) and create a **write** token.
2. In your GitHub repo → **Settings → Secrets and variables → Actions** → **New repository secret** → name it `HF_TOKEN`.

## Releasing

This project follows [semantic versioning](https://semver.org/). Releases are
created by pushing a semver tag.

```bash
git tag v0.2.0
git push origin v0.2.0
```

The [release workflow](.github/workflows/release.yml) then:

1. Creates a GitHub Release with auto-generated release notes.
2. Updates floating alias tags so consumers can pin to a major (`v0`) or
   major.minor (`v0.2`) version:

   | Push tag | Aliases created/moved |
   |---|---|
   | `v0.2.0` | `v0.2`, `v0` |
   | `v1.3.1` | `v1.3`, `v1` |

Consumers reference the action via these aliases:

```yaml
- uses: kvokka/huggingface@v0   # tracks latest v0.x.x
- uses: kvokka/huggingface@v0.1 # tracks latest v0.1.x
```
