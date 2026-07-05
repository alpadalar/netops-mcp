# Contributing to NetOpsMCP

Thanks for your interest in improving NetOpsMCP! This guide covers dev setup,
running the tests and linters exactly as CI does, and how the suite mocks the
subprocess/`psutil` layers so you can add tests without touching the network.

By participating you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## Prerequisites

- **Python >= 3.10** (CI runs 3.10, 3.11, and 3.12).
- **[uv](https://github.com/astral-sh/uv)** — install with
  `curl -LsSf https://astral.sh/uv/install.sh | sh`.
- Linux/macOS only. System tools (`curl`, `ping`, `nmap`, `dig`, …) are needed
  only for live runs — most unit tests mock them out, so you can run the bulk of
  the suite without them.

## Development setup

These are the exact commands CI runs (see `.github/workflows/`). From the repo
root:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

This installs NetOpsMCP in editable mode plus the `dev` extra (pytest,
pytest-asyncio/-cov/-mock, ruff, black, mypy, bandit; see the
`[project.optional-dependencies].dev` list in `pyproject.toml`). Always work
inside the project `.venv` (or prefix commands with `uv run`) — lint/format
results depend on the pinned `ruff`/`black` versions.

## Running the tests

```bash
uv run pytest tests/
```

Notes (config in `pyproject.toml` under `[tool.pytest.ini_options]`):

- `testpaths = ["tests"]` — a bare `pytest` only collects `tests/`.
- Coverage is on by default (`--cov=src`, HTML in `htmlcov/`). CI enforces an
  **80%** minimum via `coverage report --fail-under=80`.
- `asyncio_mode = "strict"` — async tests must be marked `@pytest.mark.asyncio`.

To iterate quickly without coverage, or to run a single test:

```bash
uv run pytest tests/ -o addopts="" -q
uv run pytest tests/test_tools.py::TestConnectivityTools::test_ping_host -o addopts="" -q
```

## Linting and formatting

CI runs three checks; the first two are **blocking**, mypy is **advisory**
(`continue-on-error`). Match them exactly:

```bash
black --check src/ tests/     # formatting (blocking); auto-fix: black src/ tests/
ruff check src/ tests/        # linting (blocking);   auto-fix: ruff check --fix src/ tests/
mypy src/ --ignore-missing-imports   # type check (advisory)
```

Configuration lives in `pyproject.toml`: black and ruff use line length 100,
target `py310`; ruff rules `E`, `F`, `B`, `I`. mypy is kept advisory because a
set of pre-existing strict-mode findings and the MCP/FastMCP SDK are outside the
current frozen-behavior release scope.

## How the tests mock the system

Every network/system tool funnels command execution through one method,
`NetOpsTool._execute_command()` (`src/netops_mcp/tools/base.py`). The suite is
built around mocking that single seam (plus `psutil` for the monitoring tools),
so the vast majority of tests run **offline and deterministically**. Fixtures
live in `tests/conftest.py`:

- **`mock_execute_command`** — patches `NetOpsTool._execute_command`; point its
  `return_value` at one of the `sample_*_output` fixtures. Patch this, **not**
  `subprocess.run`.
- **`mock_psutil`** — patches `psutil` calls for the monitoring tools
  (`system_status`, `cpu_usage`, `memory_usage`, `disk_usage`, `process_list`).
- **`stub_ssrf_resolver`** (autouse) — patches `socket.getaddrinfo` so benign
  test domains resolve offline; IP literals fall through to real classification.
- **`live_server` / `live_server_factory`** — start a real ephemeral-port
  uvicorn server driving the actually-served app for middleware/E2E tests
  (ships a plaintext key and its `sha256:` digest for the auth path).

To add a tool test: instantiate the tool class, inject a fake result via
`mock_execute_command` (or `mock_psutil`), and assert on the parsed
`List[TextContent]` response (each `.text` is JSON). Test modules must match
`test_*.py` to be collected.

## Commit and pull request guidelines

- Keep the **MCP tool surface stable** — the 26 tool names and their parameters
  must not change unless that is the explicit intent (schema snapshot tests
  guard this).
- Write focused commits with clear messages.
- Before opening a PR, confirm tests pass (`uv run pytest tests/`), lint is clean
  (`ruff check src/ tests/` and `black --check src/ tests/`), and any behavior or
  config change is reflected in the docs. Fill in the pull request template.

## Reporting bugs and security issues

- **Bugs:** open an issue using the bug report form. **Redact any API keys or
  secrets before pasting logs.**
- **Security vulnerabilities:** do **not** open a public issue — follow the
  private process in [SECURITY.md](SECURITY.md).
