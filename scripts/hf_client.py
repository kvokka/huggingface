from __future__ import annotations

import importlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

_huggingface_hub = importlib.import_module("huggingface_hub")
_huggingface_hub_errors = importlib.import_module("huggingface_hub.errors")

HfApi = _huggingface_hub.HfApi
HfHubHTTPError = _huggingface_hub_errors.HfHubHTTPError

T = TypeVar("T")


def _sleep_backoff(attempt: int, base_seconds: float = 1.0) -> None:
    time.sleep(base_seconds * (2**attempt))


def with_retries[T](fn: Callable[[], T], *, retries: int = 3) -> T:
    last_err: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            return fn()
        except (HfHubHTTPError, OSError) as e:
            last_err = e
            if attempt >= retries:
                raise
            _sleep_backoff(attempt)
    assert last_err is not None
    raise last_err


@dataclass(frozen=True)
class RepoRef:
    repo_id: str
    repo_type: str


class HfClient:
    def __init__(self, token: str) -> None:
        self._api = HfApi(token=token)

    def whoami(self) -> str:
        info = with_retries(lambda: self._api.whoami())
        name = info.get("name")
        if not name:
            raise RuntimeError("Unable to resolve token owner via whoami()")
        return str(name)

    def ensure_repo(
        self,
        *,
        repo_id: str,
        repo_type: str,
        private: bool,
        space_sdk: str | None,
    ) -> str:
        def _op() -> str:
            url = self._api.create_repo(
                repo_id=repo_id,
                repo_type=repo_type,
                private=private,
                exist_ok=True,
                space_sdk=space_sdk,
            )
            return str(url)

        return with_retries(_op)

    def upload_folder(
        self,
        *,
        folder_path: Path,
        repo_id: str,
        repo_type: str,
        commit_message: str,
        ignore_patterns: list[str] | None = None,
    ) -> str:
        folder_path = folder_path.resolve()
        if not folder_path.is_dir():
            raise ValueError(f"folder_path must be a directory: {folder_path}")

        def _op() -> str:
            url = self._api.upload_folder(
                repo_id=repo_id,
                repo_type=repo_type,
                folder_path=str(folder_path),
                commit_message=commit_message,
                ignore_patterns=ignore_patterns,
            )
            return str(url)

        return with_retries(_op)

    def set_space_variable(self, *, repo_id: str, key: str, value: str) -> None:
        def _op() -> None:
            self._api.add_space_variable(repo_id=repo_id, key=key, value=value)

        with_retries(_op)

    def set_space_secret(self, *, repo_id: str, key: str, value: str) -> None:
        def _op() -> None:
            self._api.add_space_secret(repo_id=repo_id, key=key, value=value)

        with_retries(_op)

    def repo_exists(self, *, repo_id: str, repo_type: str) -> bool:
        try:
            with_retries(lambda: self._api.repo_info(repo_id=repo_id, repo_type=repo_type))
            return True
        except HfHubHTTPError:
            return False

    def delete_repo_if_exists(self, *, repo_id: str, repo_type: str) -> bool:
        if not self.repo_exists(repo_id=repo_id, repo_type=repo_type):
            return False

        def _op() -> None:
            self._api.delete_repo(repo_id=repo_id, repo_type=repo_type)

        with_retries(_op)
        return True
