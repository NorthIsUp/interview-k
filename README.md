# python-uvx template

Python project template using:

- **mise** — toolchain management
- **uv** — package manager + builder + publisher
- **ruff** — linting + formatting
- **pyright** — type checking
- **pytest** — tests
- **hk** — pre-commit / pre-push hooks
- **semver** — versioning via `uv version --bump {patch,minor,major}`

## Quick start

```sh
mise install            # install python, uv, hk, ruff, pkl
mise run sync           # uv sync
mise run test           # pytest
mise run lint           # hk check
mise run typecheck      # pyright
mise run build          # build wheel + sdist

mise run bump-patch     # 0.1.0 -> 0.1.1
git add pyproject.toml uv.lock
git commit -m "release 0.1.1"
git push                # CI tags + releases + publishes to PyPI
```

## CI / release flow

A single GitHub Actions pipeline (`.github/workflows/ci.yml`) handles
everything because GHA workflows can't trigger each other from a tag push:

1. **test** job — lint, typecheck, pytest on every push/PR.
2. **release** job — runs only on push to `main`. If the version in
   `pyproject.toml` changed vs the previous commit, it:
   - creates an annotated git tag `v<version>`
   - builds wheel + sdist
   - publishes to PyPI via OIDC trusted publishing (no token needed)
   - creates a GitHub Release with the artifacts attached

## PyPI trusted publishing setup

In your PyPI project settings, add a trusted publisher with:

- Owner: `northisup` (your GH org/user)
- Repository: this repo
- Workflow: `ci.yml`
- Environment: `pypi`

No secrets to manage.
