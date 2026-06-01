# Contributing to ScribIA

Thank you for your interest. Contributions of all sizes are welcome — bug
reports, documentation improvements, new backend plugins, and core features.

## Development setup

```bash
git clone https://github.com/mlettieri/scribia.git
cd scribia
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Verify everything works:

```bash
pytest
ruff check src/ tests/
```

## Project layout

```
src/scribia/
  cli.py          — entry point (scribia run / init / hook / ...)
  config.py       — scribia.yaml loader
  engine/         — diff + semantic analysis (no I/O)
  updater/        — safe file writer
  backends/       — documentation backends (plugin interface)
  state/          — .scribia/state.json checkpoint
tests/            — pytest suite
plugins/          — example custom backend
templates/        — custom_backend.py.template
```

## The easiest contribution: a new backend

1. Copy `templates/custom_backend.py.template` to `src/scribia/backends/yourname.py`
2. Implement `init()`, `update()`, `persist()`
3. Register in `src/scribia/backends/loader.py` under `BUILTIN_BACKENDS`
4. Add a section to `README.md`
5. Add at least one test in `tests/`

## Code style

We use **ruff** for linting and formatting. Before every commit:

```bash
ruff format src/ tests/
ruff check src/ tests/
```

No other style guide — just keep it readable and consistent with the
surrounding code.

## Tests

```bash
pytest                          # run all tests
pytest tests/test_models.py     # run a single file
pytest --cov=scribia            # with coverage
```

Tests live in `tests/`. Unit tests should not touch the filesystem or git —
use `tmp_path` (pytest fixture) for any file operations.

## Commits and PRs

- One logical change per commit.
- Commit messages: imperative mood, present tense ("Add graphify backend",
  not "Added" or "Adding").
- Update `CHANGELOG.md` under `## [Unreleased]` for user-visible changes.
- Open a draft PR early if you want feedback before finishing.

## Licence reminder

By contributing you agree that your code will be distributed under the
[MIT with Attribution Requirement](LICENSE) licence already in this repo.
