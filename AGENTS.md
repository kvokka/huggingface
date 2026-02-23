# Agent Guidance (Critical)

This repository is a GitHub Action that deploys content to Hugging Face repositories.

## Non-negotiables

- **Hugging Face only**: do not add non-HF provider orchestration.
- **Secret safety**: never print token values or write them to artifacts.
- **Cleanup invariants**: integration tests must delete created HF resources in `always()` teardown and via a scheduled janitor.
- **Idempotency**: reruns should not fail just because repos already exist.
- **Parallel safety**: integration tests must use unique repo names per matrix job.
- **Env var contract**: integration workflows use `HF_TEST_WORKSPACE` for temp local work.

## Legacy boundary

`tmp/hugging-push/` is reference-only and must not be used at runtime.
