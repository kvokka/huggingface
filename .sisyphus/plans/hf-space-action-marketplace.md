# Work Plan: Marketplace-Ready Hugging Face Deploy Action with Optional Public Proxy

## Objective

Create a new root-level GitHub Action (composite + Python) that deploys to Hugging Face repositories (legacy-compatible `repo_type`) and optionally (default OFF) provisions a public proxy Space forwarding to a private Space API. Include real Hugging Face integration tests in GitHub Actions, full cleanup guarantees, Marketplace-ready docs, MIT license, and agent guidance.

## Decisions Locked

1. Runtime: **Composite Action + Python**.
2. Layout: **new root action layout** (legacy `tmp/hugging-push` used as reference only).
3. Proxy auth: default fallback to `hf_token`, but docs strongly recommend dedicated `proxy_hf_token`.
4. Integration tests: run on **PR + main + manual** (fork-safe secret guards).
5. Cleanup: `always()` teardown + scheduled janitor workflow.
6. Integration workspace env var name: **`HF_TEST_WORKSPACE`**.
7. Legacy compatibility: keep `repo_type` support (`space`, `model`, `dataset`).
8. Releases: release workflow + moving major tag (`v1`).

## Scope

### In

- Hugging Face deployment behavior only.
- Optional public proxy Space creation for private Space API exposure.
- GitHub Actions-based unit/integration/cleanup automation.
- Marketplace publication readiness (metadata, docs, release flow).
- Dependency transparency + Dependabot.
- AGENTS.md with critical constraints for future execution agents.

### Out

- Any non-Hugging Face provider orchestration.
- Application business logic changes.
- Runtime infra beyond what is needed for action testing/release.

## Guardrails (Metis + User Constraints)

- Keep design DRY/YAGNI/KISS; avoid framework overreach.
- Do not leak tokens into logs/CLI history.
- Integration tests must be idempotent and parallel-safe.
- Every remote resource created in tests must have deterministic cleanup path.
- Preserve legacy input behavior unless explicitly deprecated with docs.

## Target Architecture

### Action Interface (planned)

- Keep legacy inputs: `huggingface_repo`, `hf_token`, `repo_type`, `space_sdk`, `private`.
- Add focused inputs for new behavior:
  - `source_dir` (default `.`)
  - `create_proxy` (boolean, default `false`)
  - `proxy_space_suffix` (default `-proxy`)
  - `proxy_hf_token` (optional; fallback to `hf_token`)
  - `proxy_target_url` (optional override; default computed private Space URL)
  - `proxy_allow_origins` (default `*`)
  - `commit_message` (default standardized sync message)
- Provide structured outputs:
  - `repo_id`, `repo_url`, `space_url`
  - `proxy_enabled`, `proxy_repo_id`, `proxy_url`

### Internal Modules (planned)

- `scripts/deploy.py`: main orchestration + validation.
- `scripts/hf_client.py`: wrappers for HF API operations.
- `scripts/proxy_template/`: dockerized FastAPI proxy template files.
- `scripts/cleanup_resources.py`: integration cleanup helper.

### Workflow Strategy (planned)

- CI workflow for lint/unit/static checks.
- Integration workflow for real HF tests (matrix parallel jobs).
- Scheduled janitor workflow for leaked test resources.
- Release workflow for tags + moving major tag (`v1`).

## File/Artifact Plan

- `action.yml`
- `requirements.txt` and `requirements-dev.txt`
- `scripts/*.py`
- `scripts/proxy_template/{Dockerfile,main.py}`
- `tests/unit/*`
- `tests/integration/*`
- `.github/workflows/{ci.yml,integration-hf.yml,janitor.yml,release.yml}`
- `.dependabot/config.yml`
- `README.md`
- `AGENTS.md`
- `LICENSE` (MIT)

## Implementation Tasks

## TODOs (Atlas progress tracking)

- [x] Task 1 — Establish root action scaffold and legacy reference boundary
- [x] Task 2 — Define final action contract (inputs/outputs/validation rules)
- [x] Task 3 — Implement HF client abstraction for deterministic operations
- [x] Task 4 — Implement core deploy orchestration path
- [x] Task 5 — Implement optional proxy provisioning (default OFF)
- [x] Task 6 — Harden proxy template behavior for API forwarding
- [x] Task 7 — Build unit test suite for contract and orchestration logic
- [x] Task 8 — Build real HF integration tests (parallel matrix)
- [x] Task 9 — Enforce cleanup guarantees (always teardown + janitor)
- [x] Task 10 — Add CI quality gates and dependency governance
- [x] Task 11 — Produce Marketplace-grade documentation (human + agent)
- [x] Task 12 — Add AGENTS.md and legal/release artifacts
- [x] Final Verification Wave — Validate Marketplace compliance + workflows + cleanup invariants

### Task 1 — Establish root action scaffold and legacy reference boundary

**Goal:** Prepare root-level structure for the new action while explicitly preserving `tmp/hugging-push` as reference-only legacy material.

**Steps:**

1. Create root artifact skeleton listed in “File/Artifact Plan”.
2. Add explicit note in docs that `tmp/hugging-push` is historical reference, not execution path.
3. Ensure root `action.yml` is authoritative entrypoint for Marketplace.

**QA scenarios:**

- QA1: `action.yml` exists at repository root and contains valid top-level metadata keys.
- QA2: No workflow/script references runtime files under `tmp/hugging-push`.
- QA3: README clearly distinguishes legacy reference vs new action implementation.

**Done when:** root structure is publish-ready and legacy boundary is unambiguous.

### Task 2 — Define final action contract (inputs/outputs/validation rules)

**Goal:** Freeze a stable, backward-compatible interface including proxy options.

**Steps:**

1. Encode legacy inputs exactly (`huggingface_repo`, `hf_token`, `repo_type`, `space_sdk`, `private`).
2. Add new inputs with defaults from “Target Architecture”.
3. Define validation matrix:
   - `create_proxy=true` requires `repo_type=space`.
   - `proxy_hf_token` fallback to `hf_token` when empty.
   - `proxy_target_url` optional; otherwise computed from target Space id.
4. Define outputs and empty-string behavior when proxy disabled.

**QA scenarios:**

- QA1: Invalid combinations fail fast with explicit actionable error messages.
- QA2: Backward-compat workflow snippet from legacy README still runs without new inputs.
- QA3: Output keys are always present in `$GITHUB_OUTPUT` contract (proxy fields empty when off).

**Done when:** interface is documented, implemented, and test-covered for valid/invalid permutations.

### Task 3 — Implement HF client abstraction for deterministic operations

**Goal:** Centralize HF API calls for create/update/upload/delete flows and reduce duplication.

**Steps:**

1. Implement API wrapper module (`scripts/hf_client.py`) with pure functions per operation.
2. Include idempotent helpers (`ensure_repo`, `set_space_variable`, `set_space_secret`, `upload_folder`, `delete_repo_if_exists`).
3. Standardize retries/backoff for transient HF API/network failures.
4. Normalize logging to redact tokens and print only safe identifiers.

**QA scenarios:**

- QA1: Re-running same deploy flow does not produce fatal errors when repos already exist.
- QA2: Simulated transient failure path triggers retry then succeeds/fails deterministically.
- QA3: Logs contain no token values (assert by grep-style test check).

**Done when:** all external HF operations are routed through one wrapper layer with consistent behavior.

### Task 4 — Implement core deploy orchestration path

**Goal:** Build primary deploy script handling legacy repo types and configurable source directory.

**Steps:**

1. Implement `scripts/deploy.py` orchestration for argument parsing + validation + operation ordering.
2. Support `repo_type` values `space`, `model`, `dataset` with shared create/upload path.
3. Parameterize `source_dir` (remove hardcoded legacy upload path assumptions).
4. Generate deterministic commit message from `commit_message` input or default text.
5. Emit base outputs (`repo_id`, `repo_url`, `space_url`).

**QA scenarios:**

- QA1: `source_dir` set to nested folder deploys exactly that folder contents.
- QA2: `repo_type=model` and `repo_type=dataset` bypass proxy-only logic cleanly.
- QA3: Missing/invalid source directory fails before any remote mutation.

**Done when:** one script handles all baseline deployment paths without legacy path coupling.

### Task 5 — Implement optional proxy provisioning (default OFF)

**Goal:** Add controlled creation/update of public proxy Space forwarding to private Space API.

**Steps:**

1. Gate proxy logic strictly behind `create_proxy=true`.
2. Compute proxy repo id as `{target_repo}{proxy_space_suffix}` with conflict-safe handling.
3. Implement default upstream target URL from private Space domain when override not provided.
4. Apply proxy variables/secrets (`TARGET_URL`, auth token, CORS config).
5. Upload proxy template to proxy Space and emit proxy outputs.

**QA scenarios:**

- QA1: `create_proxy=false` creates no proxy repo and returns empty proxy outputs.
- QA2: `create_proxy=true` + private target results in reachable proxy URL and non-empty proxy outputs.
- QA3: `create_proxy=true` with non-space repo type fails fast with explicit guidance.

**Done when:** proxy feature is optional, explicit, and fully deterministic.

### Task 6 — Harden proxy template behavior for API forwarding

**Goal:** Ensure proxy template is production-safe enough for action-generated bootstrap behavior.

**Steps:**

1. Implement template in `scripts/proxy_template/{Dockerfile,main.py}` using FastAPI + httpx.
2. Forward core methods (`GET/POST/PUT/PATCH/DELETE/HEAD/OPTIONS`) and stream responses.
3. Preserve safe headers, strip problematic transfer/content-encoding headers.
4. Handle upstream errors with stable 5xx mapping and clear error body.
5. Add configurable CORS from `proxy_allow_origins` input.

**QA scenarios:**

- QA1: OPTIONS preflight succeeds with configured CORS headers.
- QA2: Upstream timeout/network error returns deterministic 502-like proxy response.
- QA3: Authorization forwarding uses proxy token path and never exposes raw token in response.

**Done when:** generated proxy Space behaves as predictable HTTP relay for private target API.

### Task 7 — Build unit test suite for contract and orchestration logic

**Goal:** Provide fast local confidence for validation, output contract, and flow branching.

**Steps:**

1. Add unit tests for input validation matrix and fallback behavior.
2. Mock HF client calls to verify operation order and branching.
3. Add tests ensuring output emission shape is stable across paths.
4. Include negative tests for missing secrets/invalid combinations.

**QA scenarios:**

- QA1: Unit tests fail when a required validation guard is removed.
- QA2: Branch coverage includes proxy enabled/disabled and each `repo_type` path.
- QA3: Output contract snapshot test catches accidental key renames/removals.

**Done when:** unit suite catches contract regressions without requiring network access.

### Task 8 — Build real HF integration tests (parallel matrix)

**Goal:** Validate end-to-end behavior against actual Hugging Face APIs using `HF_TOKEN`.

**Steps:**

1. Create integration workflow (`integration-hf.yml`) triggered on PR/main/manual.
2. Configure matrix cases to run in parallel (at minimum):
   - space deploy without proxy
   - private space deploy with proxy
   - legacy non-space deploy path (`model` or `dataset`)
3. Use unique repo names per case: prefix + timestamp + run_id + case id.
4. Use provided `HF_TEST_WORKSPACE` env var for temporary local test directories.
5. Disallow secret-dependent jobs on fork PRs.

**QA scenarios:**

- QA1: Matrix jobs execute concurrently (not serialized) and pass independently.
- QA2: Created resources are unique per job; no collision across parallel runs.
- QA3: Fork PR execution skips secret-requiring jobs with explicit skip messaging.

**Done when:** integration workflow proves real deployments and proxy behavior under parallel execution.

### Task 9 — Enforce cleanup guarantees (always teardown + janitor)

**Goal:** Ensure no leaked HF resources remain after test runs.

**Steps:**

1. Add workflow teardown step guarded by `if: always()` to delete all repos created by job.
2. Persist created resource ids during run for deterministic teardown.
3. Add scheduled `janitor.yml` to delete stale test resources by naming prefix + TTL policy.
4. Make janitor dry-run mode available for safe debugging.

**QA scenarios:**

- QA1: Intentional test failure still executes teardown and removes resources.
- QA2: Cancellation scenario still leaves resources recoverable by janitor next run.
- QA3: Janitor deletes only prefix-matching stale resources and leaves non-test repos untouched.

**Done when:** both immediate and delayed cleanup paths are verified and documented.

### Task 10 — Add CI quality gates and dependency governance

**Goal:** Keep maintenance sustainable for a public Marketplace action.

**Steps:**

1. Add CI workflow (`ci.yml`) for lint/unit/static checks on PR/main.
2. Add `.dependabot/config.yml` for pip and GitHub Actions ecosystems.
3. Ensure dependency declarations are explicit and minimal (runtime vs dev split).
4. Document every added dependency in README with purpose.

**QA scenarios:**

- QA1: Dependabot config validates and creates ecosystem-scoped update PRs.
- QA2: CI fails when lint/unit checks fail.
- QA3: README dependency table matches declared dependency files exactly.

**Done when:** dependency and quality gates are automated and transparent.

### Task 11 — Produce Marketplace-grade documentation (human + agent)

**Goal:** Deliver complete docs for users and autonomous agents.

**Steps:**

1. Rewrite root README with:
   - quick start
   - full input/output reference
   - proxy architecture section
   - security guidance (token scopes, dedicated proxy token recommendation)
   - integration badge
   - dependency inventory
2. Add explicit section for agent consumers (automation-oriented usage contract and pitfalls).
3. Include cleanup policy explanation and operational limits (rate limits/build time).

**QA scenarios:**

- QA1: README examples are copy-paste runnable against action contract.
- QA2: Badge URL resolves to integration workflow.
- QA3: Agent section includes machine-actionable constraints (required secrets, cleanup expectations).

**Done when:** docs cover onboarding, operations, and automation consumption end-to-end.

### Task 12 — Add AGENTS.md and legal/release artifacts

**Goal:** Encode future-agent constraints and finalize publication prerequisites.

**Steps:**

1. Create/update `AGENTS.md` with critical instructions:
   - HF-only scope
   - cleanup invariants
   - secret handling rules
   - naming prefix policy for test resources
   - required env var `HF_TEST_WORKSPACE`
2. Add MIT `LICENSE` file.
3. Add release workflow (`release.yml`) for tagged releases and moving `v1` tag.

**QA scenarios:**

- QA1: AGENTS.md is explicit enough for another agent to continue safely without hidden context.
- QA2: LICENSE is MIT and discoverable at repo root.
- QA3: Release workflow updates/maintains major tag and packages release notes.

**Done when:** governance, legal, and release mechanics are complete for Marketplace publication.

## Final Verification Wave

- Verify action metadata is Marketplace-compliant (`name`, `description`, `branding`, examples).
- Verify all workflows are green in default branch.
- Verify integration workflow badge renders in README.
- Verify cleanup works on success/failure/cancellation paths.
- Verify AGENTS.md contains all critical continuation constraints.
- Verify plan constraints are fully mapped to repo artifacts.

## Acceptance Criteria

1. Action deploys HF repo successfully for `space`, `model`, and `dataset` paths.
2. `create_proxy=false` path does not create proxy resources.
3. `create_proxy=true` path creates/updates proxy Space and returns proxy outputs.
4. Proxy path forwards requests to private Space with token-authenticated upstream calls.
5. Integration tests create real HF resources and run in parallel matrix jobs.
6. Integration teardown removes created resources even when tests fail.
7. Janitor removes leaked stale test resources by prefix/TTL policy.
8. README documents human usage + agent-oriented section + dependency inventory.
9. Dependabot monitors declared dependency ecosystems.
10. AGENTS.md captures critical operational guidance for next agents.
11. Release workflow supports Marketplace publishing with moving `v1` tag.
