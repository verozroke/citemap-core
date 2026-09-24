# Contributing

## Setting up

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

## Workflow

The project follows GitHub flow:

1. Open an issue describing the bug or feature, or pick an existing one.
2. Create a short-lived branch from `main`, named after its purpose:
   `feature/semantic-scholar-adapter`, `fix/csv-encoding`, `docs/readme-examples`.
3. Commit in small steps. Commit messages follow
   [Conventional Commits](https://www.conventionalcommits.org/):
   `feat: add year filter`, `fix: ignore self-citations`, `test: ...`,
   `docs: ...`, `ci: ...`, `refactor: ...`.
4. Open a pull request that references the issue (`Closes #12`). The CI
   pipeline must be green before merging.
5. Merge into `main`; delete the branch.

## Before opening a pull request

```bash
ruff check . && ruff format --check .
mypy
pytest --cov
```

The coverage gate is 90 %. New behaviour needs a test. When a function
implements a known formula, prefer a test against a result computed
independently (by hand or from a paper) over a test that only repeats the
function's own output.

## Releasing

1. Update the version in `pyproject.toml` and move the `Unreleased` entries in
   `CHANGELOG.md` under the new version.
2. Commit, then tag and push: `git tag v0.2.0 && git push origin v0.2.0`.
3. The release workflow tests, builds and publishes the GitHub Release.
