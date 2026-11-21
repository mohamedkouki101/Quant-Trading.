# CLAUDE.md

Context and rules for every Claude Code session in this repo. Read this file, then
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) and [README.md](README.md), before doing anything.

## Project

**momentum-lab** asks one question honestly: does vol-scaled industry momentum still earn a
premium after costs, and does a machine-learning ranker add anything beyond it?

The product is a small, verified, **event-driven backtest engine** that makes look-ahead
impossible by construction. The momentum strategy and the feature-importance study are its
first users. Data: Ken French 49 industry portfolios (1926 to 2026) and 9 sector SPDR ETFs.
Research period 1926-07 to 2005-12; locked test period 2006-01 to 2026-09.

Owner: Kouki (quant research internship portfolio project). Free tools and data only.

## Where things are

| File | What it is |
|---|---|
| `IMPLEMENTATION_PLAN.md` | **The task list you follow.** Ordered tasks with checkboxes and acceptance criteria. Its "Corrections" table overrides the plan docs |
| `README.md` | Progress tracker Kouki reads. Update it after every task |
| `docs/plan/PLAN.md` | Full design: timing contract (§3.2), interfaces (§3.3), costs (§3.4), repo layout (§4), data (§5), methods (§7), tests (§9) |
| `docs/plan/ROADMAP.md` | Full task table for all phases P0 to P8 |
| `docs/plan/RESEARCH_INVENTORY.md`, `docs/plan/PHASE1_RESEARCH.md` | Research behind the plan, sources, verified facts |
| `docs/plan/*` (others) | Interview kit, learning path, audience research, HTML version of the plan |
| `docs/DECISIONS.md` | Decision log. Every deviation from the plan goes here |
| `PREREGISTRATION.md` | Hypotheses and thresholds, fixed before results. Never edit after Kouki tags it, except the Deviations section |

`docs/plan/` is frozen reference material. Do not edit it. Record changes in
`docs/DECISIONS.md` and, if they change a task, in `IMPLEMENTATION_PLAN.md`.

## Hard rules

1. **No git.** Kouki handles git and GitHub. Never run `git init`, `add`, `commit`, `tag`,
   `branch`, `checkout`, `stash`, `push`, `pull`, `reset` or anything else that changes the
   repo or its history. Program code may read git state (`git rev-parse HEAD`,
   `git status --porcelain`, `git tag -l`) for the ledger and test vault only.
2. **Work locally** in this folder on Kouki's Windows machine. No cloud services, no
   deployments, no GitHub API calls.
3. **One task at a time**, in the order of `IMPLEMENTATION_PLAN.md`. Do not start a task whose
   dependencies are not ticked. Do not start a new phase without Kouki's go-ahead.
4. **Stop at Kouki checkpoints** (boxes marked **Kouki**: commits, tags, pushes, CI check,
   accounts, API keys). Say exactly what Kouki needs to do, then wait.
5. **No look-ahead, ever.** Strategy code reads data only through `AsOfView`. `fill_lag >= 1`.
   No forward-filling of returns. Scalers and models are fit inside training folds only.
6. **The test period stays locked.** Never read, plot or compute anything on 2006-01 onward
   until task T-2, and never set `MOMLAB_UNLOCK_TEST`.
7. **Pre-registration comes first.** No strategy return is computed before
   `PREREGISTRATION.md` v1 exists.
8. **Every trial counts.** Strategy runs from P4 onward go through the append-only ledger.
   Never delete or rewrite ledger lines.
9. **Never invent numbers.** Every figure in docs comes from code output. If a test fails or a
   threshold is missed, say so and log it. Do not tune tolerances to make a test pass.
10. **No data or secrets in the repo.** Raw and processed data stay in gitignored folders;
    keys live in `.env` only and are never printed. Ken French data is downloaded by code,
    never committed.
11. Everything that shows performance is labelled "hypothetical backtest, not investment
    advice".

## After every task (definition of done)

1. Run `uv run python tasks.py check` (lint, format check, mypy, tests). All must pass.
2. Tick the task's boxes in `IMPLEMENTATION_PLAN.md`.
3. Update `README.md`: the task's row in the status table, "Current focus", "Waiting on
   Kouki" and a change-log line (date, task ID, one sentence).
4. If anything differed from the plan, add an entry to `docs/DECISIONS.md`.
5. Stop and give Kouki a short summary: what was built, test results, any deviation, files
   changed, and a suggested commit message in the form `D-2: parse and clean Ken French files`.

## Environment and commands

- Windows, PowerShell. Python 3.13 managed by **uv**. Use `uv run ...`; do not use pip or conda.
- Task runner: `uv run python tasks.py <target>` (`check`, `test`, `test-fast`, `test-data`,
  `lint`, `format`, `typecheck`, `ci`, `data`). There is no Makefile; where the plan says
  `make X`, use `tasks.py X`.
- Add dependencies with `uv add` / `uv add --dev` so `uv.lock` stays current.
- Use forward slashes or `pathlib` in code; never hard-code `C:\` paths.
- Real-data tests are marked `@pytest.mark.data` and need `tasks.py data` first.

## Code conventions

- Package `momlab` in `src/momlab/`, layout per PLAN §4.
- Type hints on every function; `mypy src` clean. Docstrings on public functions, with units
  (decimal returns, weights, bps).
- ruff for lint and format (line length 100).
- pandas 3 (copy-on-write is the default). Inside the event loop prefer NumPy arrays.
- Returns are simple decimal returns (0.01 = 1%). Dates are month-end or trading-day
  timestamps, never strings.
- Seeds: one `seed` in config, derived with `numpy.random.SeedSequence(seed).spawn(n)`.
- Tests: hand-computed expected values written in the test file, not produced by the code
  under test. Name tests after the leakage items they guard where relevant (`test_vault_locked`).
- Coverage: 85% overall; 100% for `engine.py`, `execution.py`, `costs.py`, `data/handler.py`.

## When unsure

If the plan is ambiguous or wrong, pick the reading most consistent with PLAN.md's intent,
write it in `docs/DECISIONS.md`, and mention it in the task summary. Ask Kouki before anything
that changes a hypothesis, threshold, data period or the trial budget.
