---
name: python-api-tdd
description: Enforce an approved-plan-first TDD workflow, maintainable Python design, and architecture quality gates for changes in apps/api, packages/db, and packages/ml in electoral-drift. Use when implementing, fixing, or refactoring the FastAPI application, SQLAlchemy database package, or ML package. Do not use for packages/ingestion or frontend work.
---

# Python API TDD

Implement Python API, database, and ML changes through explicit, gated states. Treat `AGENTS.md`
as the source of truth for repository architecture and code-quality rules.

## Scope

- Operate only in `apps/api`, `packages/db`, and `packages/ml` when it exists.
- Do not apply this workflow to `packages/ingestion` or frontend code.
- Read the applicable `AGENTS.md`, relevant code, tests, package manifests, and architecture
  configuration before proposing changes.
- Keep the change focused. Do not perform unrelated cleanup.

## Workflow

Follow every state in order. Do not combine or skip states.

### 1. Plan

Present a decision-complete plan covering:

- observable behaviour and explicit invariants;
- affected responsibilities and dependency direction;
- REP, CCP, and CRP impact;
- expected comments or docstrings for multi-step and non-obvious code;
- test cases, edge cases, and acceptance criteria.

Stop after presenting the plan. Do not edit tests or implementation until the user explicitly
accepts it.

### 2. RED

Write the smallest tests that express the accepted behaviour. Prefer observable behaviour,
deterministic inputs, and focused tests over implementation-detail assertions or excessive mocks.

Run the narrowest relevant test command and confirm:

- the new test fails;
- the failure is caused by the missing or incorrect behaviour;
- the failure is not an import, syntax, fixture, or environment error.

Report the RED evidence before implementing production code.

### 3. GREEN

Implement the smallest correct solution that makes the accepted tests pass.

- Follow existing project patterns unless they conflict with `AGENTS.md`.
- Keep business decisions separate from HTTP, database, filesystem, environment, and other I/O.
- Add abstractions only for a real boundary, a concrete testing need, or stable identical reuse.
- Add concise section comments where they help a reader scan the stages of a multi-step flow.
- Use comments to explain sequence, intent, invariants, and reasons; do not narrate obvious lines.
- Add concise docstrings to public APIs and non-obvious domain behaviour.

Run the narrow relevant tests until they pass.

### 4. Refactor

Simplify names, control flow, responsibilities, and comments without expanding scope or changing
behaviour. Keep tests green. Remove speculative abstractions and stale or redundant comments.

### 5. Self-review

Review the complete diff and correct any issue found:

- Is there a simpler correct design with fewer concepts?
- Is the main path shallow, explicit, and locally understandable?
- Are side effects and transaction boundaries visible?
- Are errors handled at the layer with enough context?
- Is there accidental repeated work, an N+1 query, or unjustified complexity?
- Does REP keep reusable and released units aligned?
- Does CCP keep code that changes for the same reason together?
- Does CRP avoid forcing consumers to depend on unused capabilities?
- Are dependencies declared in the package that uses them?
- Can each changed file and multi-step function be scanned quickly?
- Do comments guide the sequence and explain why without restating code?
- Are all comments current, and is any comment hiding code that should instead be simplified?
- Are tests focused on behaviour and important edge cases?
- Did the diff introduce unrelated changes?

### 6. Quality gate

Run every applicable command from the repository root:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy apps/api packages/db
uv run lint-imports
```

If `packages/ml` exists, append it to the mypy command and ensure `.importlinter` contains the ML
contracts required by `AGENTS.md`.

Do not declare completion if a command was skipped or failed. Fix the cause without weakening
tests, types, or architecture rules. Do not add an Import Linter exception without explicit
justification and user approval.

### 7. Report

Report:

- implemented behaviour and important design decisions;
- RED evidence;
- exact validation commands and outcomes;
- REP, CCP, and CRP conclusions;
- remaining trade-offs or failures.

## Non-negotiable rules

- Never implement before plan approval and a valid RED result.
- Never delete, weaken, or rewrite a test merely to obtain GREEN.
- Never introduce speculative extension points or unused configuration.
- Never add comments mechanically to every line.
- Never leave comments that contradict the implementation.
- Never claim that Import Linter alone proves REP, CCP, or CRP compliance.
