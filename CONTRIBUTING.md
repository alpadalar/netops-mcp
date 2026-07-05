# Contributing to NetOpsMCP

Thanks for your interest in improving NetOpsMCP! This is a Python/FastMCP-based
network operations MCP server that wraps OS-level diagnostic tools (`ping`,
`traceroute`, `mtr`, `nmap`, DNS lookups, HTTP requests, system monitoring)
behind the Model Context Protocol. This guide covers how to set up a development
environment, run the tests and linters exactly as CI does, and how the test
suite mocks the subprocess/`psutil` layers so you can add tests without touching
the network.

By participating in this project you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development setup](#development-setup)
- [Running the tests](#running-the-tests)
- [Linting and formatting](#linting-and-formatting)
- [How the tests mock the system](#how-the-tests-mock-the-system)
- [Adding a new tool test](#adding-a-new-tool-test)
- [Commit and pull request guidelines](#commit-and-pull-request-guidelines)
- [Reporting bugs and security issues](#reporting-bugs-and-security-issues)

## Prerequisites

- **Python >= 3.10** (the project targets 3.10, 3.11, and 3.12 in CI).
- **[uv](https://github.com/astral-sh/uv)** — the project's package manager.
  Install it once with:

  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

- **System tools** for running the tools live or the full network-dependent
  tests: `curl`, `ping`, `traceroute`, `mtr`, `telnet`, `nc`, `nmap`,
  `netstat`, `ss`, `nslookup`, `dig`, `host`, `arp`, `arping`. Most of the unit
  tests mock these out (see [How the tests mock the system](#how-the-tests-mock-the-system)),
  so you can run the bulk of the suite without them installed. Linux/macOS only —
  the network tools are OS-specific and Windows is not supported.

## Development setup

These are the exact commands CI runs (see `.github/workflows/lint.yml` and
`.github/workflows/test.yml`). Run them from the repository root:

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

This creates a virtual environment in `.venv/` and installs NetOpsMCP in
editable mode together with the `dev` extra (pytest, pytest-asyncio,
pytest-cov, pytest-mock, ruff, black, mypy, bandit, and friends — see the
`[project.optional-dependencies].dev` list in `pyproject.toml`).

> Always work inside the project `.venv` (or prefix commands with `uv run`).
> The system `python3` / `pytest` / `black` may be a different version than the
> lockfile-pinned toolchain, and lint/format results depend on the exact
> `ruff`/`black` versions.

## Running the tests

Run the full suite the way CI does:

```bash
uv run pytest tests/
```

A few things to know about the test configuration (all defined in
`pyproject.toml` under `[tool.pytest.ini_options]`):

- **`testpaths = ["tests"]`** — a bare `pytest` (or `uv run pytest`) only
  collects the `tests/` directory. Exploratory scripts elsewhere in the tree are
  intentionally *not* collected.
- **Coverage is on by default** — `addopts` includes `--cov=src`,
  `--cov-report=html`, and `--cov-report=term-missing`. Coverage HTML lands in
  `htmlcov/` (gitignored). CI enforces an **80%** minimum via
  `coverage report --fail-under=80`.
- **`asyncio_mode = "strict"`** — async tests must be explicitly marked with
  `@pytest.mark.asyncio`; there is no auto-mode.

To iterate quickly without the coverage overhead you can disable the default
`addopts`:

```bash
uv run pytest tests/ -o addopts="" -q
```

To run a single file or test:

```bash
uv run pytest tests/test_tools.py -o addopts="" -q
uv run pytest tests/test_tools.py::TestConnectivityTools::test_ping_host -o addopts="" -q
```

## Linting and formatting

CI runs three checks; the first two are **blocking**, mypy is **advisory**
(`continue-on-error`). Match them exactly:

```bash
# Formatting check (blocking) — same as CI's `black --check src/ tests/`
black --check src/ tests/
# Auto-format before committing:
black src/ tests/

# Linting (blocking) — same as CI's `ruff check src/ tests/`
ruff check src/ tests/
# Auto-fix the fixable rules:
ruff check --fix src/ tests/

# Type checking (advisory — does not fail CI)
mypy src/ --ignore-missing-imports
```

Tooling configuration lives in `pyproject.toml`:

- **black** — line length 100, target `py310`.
- **ruff** — rules `E`, `F`, `B`, `I`; line length 100; target `py310`. Some
  behavior-frozen residuals are handled via `[tool.ruff.per-file-ignores]`.
- **mypy** — strict settings, `python_version = "3.10"`. It is kept advisory
  because the MCP/FastMCP SDK and a set of pre-existing strict-mode findings are
  outside the current frozen-behavior release scope.

Before opening a PR, make sure `black --check src/ tests/` and
`ruff check src/ tests/` both exit 0 and the test suite is green.

## How the tests mock the system

Every network/system tool in NetOpsMCP ultimately shells out through one method:
`NetOpsTool._execute_command()` in `src/netops_mcp/tools/base.py`. The test
suite is built around mocking that single seam (plus `psutil` for the monitoring
tools), so the vast majority of tests run **offline and deterministically**. All
fixtures live in `tests/conftest.py`.

### `mock_execute_command` — the canonical subprocess seam

```python
@pytest.fixture
def mock_execute_command():
    with patch.object(NetOpsTool, "_execute_command") as mock:
        yield mock
```

New tool tests should patch **`NetOpsTool._execute_command`** (via this
fixture), **not** `subprocess.run`. `_execute_command` is the one place every
tool funnels command execution through, so mocking it gives you full control
over the tool's result without depending on the shape of the underlying
`subprocess` call. Point the mock's `return_value` at one of the
`sample_*_output` fixtures below.

### `mock_psutil` — for the monitoring tools

The `MonitoringTools` (`system_status`, `cpu_usage`, `memory_usage`,
`disk_usage`, `process_list`) read `psutil` directly rather than shelling out.
The `mock_psutil` fixture patches `psutil.cpu_percent`, `psutil.virtual_memory`,
`psutil.disk_usage`, and `psutil.process_iter` with sensible defaults, and
yields a dict of the individual mocks so a test can override any of them.

### `stub_ssrf_resolver` — autouse offline DNS

The SSRF classifier resolves host/URL inputs through `socket.getaddrinfo`
*before* classifying the resulting IP. To keep the whole suite offline and
deterministic, the **autouse** `stub_ssrf_resolver` fixture patches
`socket.getaddrinfo` (not an internal `_resolve` helper) so a small set of
benign test domains (`example.com`, `google.com`, `httpbin.org`,
`api.github.com`) map to a fixed global IP (`93.184.216.34`). **IP literals and
numeric encodings are deliberately *not* intercepted** — they fall through to
the real (offline) `getaddrinfo` so the SSRF corpus still exercises genuine
`inet_aton` normalization. Because it is autouse, you get offline DNS for free;
you only interact with it if you need a new benign domain mapped.

### `sample_*_output` — the result dict shape

`_execute_command` returns a dict shaped like:

```python
{
    "success": True,       # bool — command exit was treated as success
    "stdout": "...",       # str  — captured standard output
    "stderr": "",          # str  — captured standard error
    "return_code": 0,      # int  — process exit code
    "command": "ping ...", # str  — the command that was run
}
```

The `sample_curl_output`, `sample_ping_output`, `sample_traceroute_output`,
`sample_mtr_output`, `sample_nslookup_output`, `sample_dig_output`,
`sample_nmap_output`, `sample_ss_output`, `sample_netstat_output`,
`sample_arp_output` (and the ping edge-case variants) fixtures provide realistic
values in exactly this shape. Feed one into `mock_execute_command.return_value`
to drive a tool test.

### `run_live_server` / `live_server` — the E2E harness

For middleware or end-to-end HTTP tests, use the live-server harness. It starts
a **real ephemeral-port uvicorn server** in a daemon thread driving
`NetOpsMCPHTTPServer.build_http_app()` — the app that is actually served — and
polls `GET /health` for readiness. This is deliberately *not* Starlette's
`TestClient` (which can pass even when the served-app wiring is broken) and not
`server.run()` (which calls `signal.signal` off the main thread and raises).
The module-scoped `live_server` fixture uses a generous rate limit; use
`live_server_factory` when you need a per-test config (for example a tight rate
limit to assert the 429 path). The harness ships a plaintext API key
(`e2e-test-key`) and its `sha256:` digest so you can exercise the auth path.

## Adding a new tool test

1. Create or extend a test module under `tests/` (it must match
   `test_*.py` to be collected).
2. Instantiate the tool class and inject a fake command result via
   `mock_execute_command` (or `mock_psutil` for monitoring tools).
3. Assert on the parsed `List[TextContent]` response — tools always return a
   list of `TextContent` whose `.text` is JSON.
4. Run `uv run pytest tests/your_module.py -o addopts="" -q`, then
   `ruff check src/ tests/` and `black --check src/ tests/`.

## Commit and pull request guidelines

- Keep the **MCP tool surface stable** — the 26 tool names and their parameters
  must not change unless that is the explicit intent of the change (the schema
  snapshot tests in `tests/` guard this).
- Write focused commits with clear messages.
- Before opening a PR, confirm: tests pass (`uv run pytest tests/`), lint is
  clean (`ruff check src/ tests/` and `black --check src/ tests/`), and any
  behavior or configuration change is reflected in the docs.
- Fill in the pull request template — it mirrors the checklist above.

## Reporting bugs and security issues

- **Bugs:** open an issue using the bug report form
  (`.github/ISSUE_TEMPLATE/bug_report.yml`). It asks for your OS, Python
  version, transport (stdio/HTTP), MCP client, and the affected tool so we can
  reproduce quickly. **Redact any API keys or secrets before pasting logs.**
- **Security vulnerabilities:** do **not** open a public issue. Follow the
  private disclosure process in [SECURITY.md](SECURITY.md).
