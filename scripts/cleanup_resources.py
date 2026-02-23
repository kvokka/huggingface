from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from scripts.hf_client import HfClient


@dataclass(frozen=True)
class Resource:
    repo_type: str
    repo_id: str


def parse_resources_file(path: Path) -> list[Resource]:
    resources: list[Resource] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"Invalid resource line (expected: '<type> <repo_id>'): {raw!r}")
        repo_type, repo_id = parts
        resources.append(Resource(repo_type=repo_type, repo_id=repo_id))
    return resources


def main() -> None:
    parser = argparse.ArgumentParser(description="Best-effort cleanup of HF test resources")
    parser.add_argument("--hf-token", required=True)
    parser.add_argument("--resources-file", required=True)
    args = parser.parse_args()

    resources_file = Path(args.resources_file)
    if not resources_file.exists():
        raise FileNotFoundError(f"resources file not found: {resources_file}")

    resources = parse_resources_file(resources_file)
    client = HfClient(token=args.hf_token)

    for r in resources:
        try:
            client.delete_repo_if_exists(repo_id=r.repo_id, repo_type=r.repo_type)
        except Exception as e:
            print(f"cleanup: failed to delete {r.repo_type}:{r.repo_id}: {e}")


if __name__ == "__main__":
    main()
