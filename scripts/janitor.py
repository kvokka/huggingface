from __future__ import annotations

import argparse
import datetime as dt
import importlib

_huggingface_hub = importlib.import_module("huggingface_hub")
HfApi = _huggingface_hub.HfApi


def utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


def is_older_than(ts: dt.datetime, *, days: int) -> bool:
    return utcnow() - ts >= dt.timedelta(days=days)


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete stale HF test repos by prefix + TTL")
    parser.add_argument("--hf-token", required=True)
    parser.add_argument("--prefix", required=True)
    parser.add_argument("--ttl-days", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    api = HfApi(token=args.hf_token)
    who = api.whoami()
    owner = str(who.get("name") or "")
    if not owner:
        raise RuntimeError("janitor: unable to resolve owner")

    deleted = 0

    for space in api.list_spaces(author=owner):
        repo_id = str(space.id)
        name = repo_id.split("/", 1)[1]
        if not name.startswith(args.prefix):
            continue
        last_mod = space.last_modified
        if last_mod is None or not is_older_than(last_mod, days=args.ttl_days):
            continue
        if args.dry_run:
            print(f"dry-run: delete space {repo_id} (last_modified={last_mod.isoformat()})")
        else:
            api.delete_repo(repo_id=repo_id, repo_type="space")
            deleted += 1

    for ds in api.list_datasets(author=owner):
        repo_id = str(ds.id)
        name = repo_id.split("/", 1)[1]
        if not name.startswith(args.prefix):
            continue
        last_mod = ds.last_modified
        if last_mod is None or not is_older_than(last_mod, days=args.ttl_days):
            continue
        if args.dry_run:
            print(f"dry-run: delete dataset {repo_id} (last_modified={last_mod.isoformat()})")
        else:
            api.delete_repo(repo_id=repo_id, repo_type="dataset")
            deleted += 1

    for model in api.list_models(author=owner):
        repo_id = str(model.id)
        name = repo_id.split("/", 1)[1]
        if not name.startswith(args.prefix):
            continue
        last_mod = model.last_modified
        if last_mod is None or not is_older_than(last_mod, days=args.ttl_days):
            continue
        if args.dry_run:
            print(f"dry-run: delete model {repo_id} (last_modified={last_mod.isoformat()})")
        else:
            api.delete_repo(repo_id=repo_id, repo_type="model")
            deleted += 1

    print(f"janitor: deleted {deleted} repo(s)")


if __name__ == "__main__":
    main()
