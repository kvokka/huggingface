import pytest

from scripts.deploy import (
    build_ui_url,
    compute_default_space_runtime_url,
    compute_proxy_repo_id,
    compute_repo_id,
    normalize_repo_type,
    parse_bool,
)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("true", True),
        ("TRUE", True),
        ("1", True),
        ("yes", True),
        ("on", True),
        ("false", False),
        ("0", False),
        ("no", False),
        ("off", False),
        ("", False),
    ],
)
def test_parse_bool(value: str, expected: bool) -> None:
    assert parse_bool(value) is expected


def test_parse_bool_invalid() -> None:
    with pytest.raises(ValueError):
        parse_bool("maybe")


def test_normalize_repo_type() -> None:
    assert normalize_repo_type("SPACE") == "space"
    assert normalize_repo_type("model") == "model"
    assert normalize_repo_type("dataset") == "dataset"


def test_normalize_repo_type_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_repo_type("spaces")


def test_build_ui_url() -> None:
    assert build_ui_url("a/b", "space") == "https://huggingface.co/spaces/a/b"
    assert build_ui_url("a/b", "dataset") == "https://huggingface.co/datasets/a/b"
    assert build_ui_url("a/b", "model") == "https://huggingface.co/a/b"


def test_compute_repo_id_uses_owner_when_no_namespace() -> None:
    repo_id = compute_repo_id(
        huggingface_repo="my-space",
        github_repo="octo/repo",
        token_owner="me",
    )
    assert repo_id == "me/my-space"


def test_compute_repo_id_preserves_namespace() -> None:
    repo_id = compute_repo_id(
        huggingface_repo="org/name",
        github_repo="octo/repo",
        token_owner="me",
    )
    assert repo_id == "org/name"


def test_compute_repo_id_defaults_to_github_repo_when_sentinel() -> None:
    repo_id = compute_repo_id(
        huggingface_repo="same_with_github_repo",
        github_repo="octo/repo",
        token_owner="me",
    )
    assert repo_id == "octo/repo"


def test_compute_proxy_repo_id() -> None:
    assert compute_proxy_repo_id(target_repo_id="a/b", suffix="-proxy") == "a/b-proxy"


def test_compute_default_space_runtime_url() -> None:
    assert compute_default_space_runtime_url(repo_id="a/b") == "https://a-b.hf.space"
