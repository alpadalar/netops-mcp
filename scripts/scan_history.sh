#!/usr/bin/env bash
#
# scan_history.sh — NetOpsMCP publication HARD GATE (REL-10)
#
# Scans the ENTIRE git history (all refs) before the repository is made public,
# and reports whether the history is publication-clean.
#
# It checks two independent surfaces:
#
#   1. Secrets / credentials in any commit on any ref:
#        - private-key blocks (RSA/OPENSSH/EC/DSA/PGP/PRIVATE)
#        - AWS access key IDs (AKIA...)
#        - GitHub / Slack provider tokens
#        - real bearer tokens (excluding documented placeholders)
#
#   2. Planning / AI-tool / coverage / log artifacts that must never ship:
#        .planning, CLAUDE.md, .claude, get-shit-done, .codex, .cursor,
#        .agents, htmlcov, logs, .impeccable
#        (each must have ZERO commits across all refs)
#
# Benign high-entropy allowlist (see RESEARCH Pitfall 3):
#   - uv.lock package-integrity hashes  (files.pythonhosted.org  sha256:<64hex>)
#   - the README example digest 0f70...25 (= sha256 of the literal "YOUR-KEY")
#
# Tooling: if `gitleaks` (with .gitleaks.toml) or `detect-secrets` are installed
# they augment the scan, but a zero-install patterned baseline over
# `git log -p --all` ALWAYS runs so the gate is deterministic on any host
# (CONTEXT-sanctioned fallback). The script is READ-ONLY — it never rewrites
# history.
#
# Exit codes:
#   0  PASS   — history is publication-clean (0 findings). Gate is green.
#   1  BLOCKER— at least one finding. DO NOT push/publish. Surface to a human.
#              History rewrite is irreversible (force-push) and is NEVER done here.
#
# Usage:  bash scripts/scan_history.sh

set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT" || { echo "FATAL: cannot cd to repo root" >&2; exit 2; }

FINDINGS=0
README_EXAMPLE_DIGEST='sha256:0f70dbbe4175927d0c7ff3bdc45622f13e6a5d306248731395a8995974effe25'

section() { printf '\n=== %s ===\n' "$1"; }

# Count matching lines robustly (wc always exits 0; empty input -> 0).
count_matches() { grep -icE "$1" 2>/dev/null || true; }

# ---------------------------------------------------------------------------
# 0. Header
# ---------------------------------------------------------------------------
printf 'NetOpsMCP publication hard gate (REL-10)\n'
printf 'repo: %s\n' "$REPO_ROOT"
printf 'refs scanned: %s | commits (all refs): %s\n' \
    "$(git for-each-ref --format='%(refname)' | wc -l | tr -d ' ')" \
    "$(git rev-list --all --count)"

# ---------------------------------------------------------------------------
# 1. Forbidden artifact paths — must have 0 commits across ALL refs
# ---------------------------------------------------------------------------
section "Artifact absence check (all refs)"
ARTIFACT_PATHS=(.planning CLAUDE.md .claude get-shit-done .codex .cursor .agents htmlcov logs .impeccable)
for p in "${ARTIFACT_PATHS[@]}"; do
    n=$(git log --all --oneline -- "$p" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$n" -ne 0 ]; then
        printf 'FINDING: %-16s appears in %s commit(s) of git history\n' "$p" "$n"
        FINDINGS=$((FINDINGS + 1))
    else
        printf 'ok: %-16s (0 commits)\n' "$p"
    fi
done

# ---------------------------------------------------------------------------
# 2. Targeted secret patterns over the full-history diff (all refs)
# ---------------------------------------------------------------------------
# The ENTIRE tracked tree is scanned — including this script and .gitleaks.toml.
# A hard publication gate must not carry a blind spot: a real secret committed
# into the scanner's own definition files would otherwise ship undetected. The
# only pattern that used to self-match the scanner's source (the redundant PEM
# filename check) has been removed (it was fully covered by the private-key
# block pattern below), so no whole-file self-exclusion is needed.
section "Targeted secret patterns (git log -p --all, full tree)"
DIFF_ALL="$(git log -p --all -- .)"

check_pattern() {
    local label="$1" regex="$2" hits
    hits=$(printf '%s\n' "$DIFF_ALL" | count_matches "$regex")
    hits=${hits:-0}
    if [ "$hits" -ne 0 ]; then
        printf 'FINDING: %-34s %s hit(s)\n' "$label" "$hits"
        FINDINGS=$((FINDINGS + 1))
    else
        printf 'ok: %-34s 0\n' "$label"
    fi
}

check_pattern "private-key blocks"          'BEGIN (RSA|OPENSSH|EC|DSA|PGP|PRIVATE) '
check_pattern "AWS access key id (AKIA)"     'AKIA[0-9A-Z]{16}'
check_pattern "GitHub token (ghp/gho/ghs/ghu)" 'gh[posu]_[A-Za-z0-9]{36}'
check_pattern "Slack token (xox...)"         'xox[baprs]-[0-9A-Za-z-]{10,}'
check_pattern "Google API key (AIza...)"     'AIza[0-9A-Za-z_-]{35}'
# NOTE: a separate PEM private-key filename pattern was intentionally removed.
# It was fully subsumed by the private-key-block check above (which already
# matches real PEM header lines), and it was the sole pattern that self-matched
# this script's own source — the reason the scanner-def files used to be
# excluded from the diff wholesale. Do NOT re-add a literal PEM header string
# here: it would self-match the private-key-block check and fail this gate.

# Real bearer tokens on ADDED lines, excluding documented placeholders.
# The placeholder allowlist is anchored to the TOKEN (the value right after
# "Bearer "), not to the whole line (WR-02): a line whose bearer value is a real
# token but which also happens to contain a benign word like "example" elsewhere
# (e.g. a trailing "# example config" comment) must still be flagged.
BEARER_DETECT='^\+.*Bearer [A-Za-z0-9_.-]{20,}'
BEARER_PLACEHOLDER='Bearer (YOUR|EXAMPLE|XXXX|PLACEHOLDER|CHANGEME|<|\.\.\.)'
section "Real bearer tokens (added lines, excluding placeholders)"
bearer_hits=$(printf '%s\n' "$DIFF_ALL" \
    | grep -iE "$BEARER_DETECT" 2>/dev/null \
    | grep -viE "$BEARER_PLACEHOLDER" 2>/dev/null \
    | wc -l | tr -d ' ')
bearer_hits=${bearer_hits:-0}
if [ "$bearer_hits" -ne 0 ]; then
    printf 'FINDING: real bearer token(s): %s\n' "$bearer_hits"
    printf '%s\n' "$DIFF_ALL" | grep -iE "$BEARER_DETECT" \
        | grep -viE "$BEARER_PLACEHOLDER" | head -10
    FINDINGS=$((FINDINGS + 1))
else
    printf 'ok: real bearer tokens 0\n'
fi

# ---------------------------------------------------------------------------
# 3. High-entropy sha256 triage — every hit must be allowlisted
# ---------------------------------------------------------------------------
section "High-entropy sha256 triage (allowlist: uv.lock hashes + README example)"
# Allowlist PER TOKEN, not per line (WR-02). A naive `grep -v` of any line that
# mentions files.pythonhosted.org or the README digest would silently drop a
# real secret co-located on the same line. Instead:
#   1. neutralize only the genuine uv.lock package-hash token — recognized by
#      the structured `url = "https://files.pythonhosted.org/...",
#      hash = "sha256:<hex>"` shape (a bare mention of the URL is NOT enough);
#   2. extract every remaining sha256 token individually (grep -oiE);
#   3. drop only the exact README example-digest token.
# Anything left is a finding, even if it shared a line with a benign hash.
# Residual (documented): a secret injected into the exact structured uv.lock
# url+hash position is still trusted — the same public-lockfile assumption the
# .gitleaks.toml `^uv\.lock$` path allowlist already makes.
UVLOCK_HASH_STRUCT='url = "https://files\.pythonhosted\.org/[^"]*", hash = "sha256:[a-f0-9]{16,}"'
UNEXPECTED_SHA_LIST=$(printf '%s\n' "$DIFF_ALL" \
    | grep -iE 'sha256:[a-f0-9]{16,}' 2>/dev/null \
    | sed -E "s#${UVLOCK_HASH_STRUCT}#UVLOCK_PKG_HASH#g" \
    | grep -oiE 'sha256:[a-f0-9]{16,}' 2>/dev/null \
    | grep -viF "$README_EXAMPLE_DIGEST" 2>/dev/null)
UNEXPECTED_SHA=$(printf '%s' "$UNEXPECTED_SHA_LIST" | grep -c . )
UNEXPECTED_SHA=${UNEXPECTED_SHA:-0}
TOTAL_SHA=$(printf '%s\n' "$DIFF_ALL" | grep -oiE 'sha256:[a-f0-9]{16,}' 2>/dev/null | grep -c .)
TOTAL_SHA=${TOTAL_SHA:-0}
if [ "$UNEXPECTED_SHA" -ne 0 ]; then
    printf 'FINDING: %s sha256 token(s) outside the uv.lock/README allowlist:\n' "$UNEXPECTED_SHA"
    printf '%s\n' "$UNEXPECTED_SHA_LIST" | head -20
    FINDINGS=$((FINDINGS + 1))
else
    printf 'ok: all %s sha256 token(s) allowlisted (uv.lock package hashes + README example digest)\n' "$TOTAL_SHA"
fi

# ---------------------------------------------------------------------------
# 4. Scanner augmentation (optional — patterned baseline above is authoritative)
# ---------------------------------------------------------------------------
section "Scanner augmentation (optional)"
DS_BIN=""
if command -v detect-secrets >/dev/null 2>&1; then
    DS_BIN="detect-secrets"
elif [ -x "$REPO_ROOT/.venv/bin/detect-secrets" ]; then
    DS_BIN="$REPO_ROOT/.venv/bin/detect-secrets"
fi

if command -v gitleaks >/dev/null 2>&1; then
    echo "gitleaks found — scanning all refs with .gitleaks.toml allowlist"
    if gitleaks detect --source . --config .gitleaks.toml --log-opts="--all" --redact -v; then
        echo "ok: gitleaks reported no findings"
    else
        echo "FINDING: gitleaks reported findings (review output above)"
        FINDINGS=$((FINDINGS + 1))
    fi
elif [ -n "$DS_BIN" ]; then
    echo "detect-secrets found ($DS_BIN) — scanning tracked files"
    if "$DS_BIN" scan --all-files >/tmp/.ds_scan.json 2>/dev/null; then
        ds_secrets=$(grep -c '"type"' /tmp/.ds_scan.json 2>/dev/null || echo 0)
        if [ "${ds_secrets:-0}" -ne 0 ]; then
            echo "FINDING: detect-secrets flagged ${ds_secrets} potential secret(s) — review /tmp/.ds_scan.json"
            FINDINGS=$((FINDINGS + 1))
        else
            echo "ok: detect-secrets reported no findings"
        fi
    fi
    rm -f /tmp/.ds_scan.json
else
    echo "note: no gitleaks/detect-secrets on PATH — the zero-install patterned"
    echo "      baseline above is the authoritative gate (CONTEXT-sanctioned)."
fi

# ---------------------------------------------------------------------------
# 5. Result
# ---------------------------------------------------------------------------
section "RESULT"
if [ "$FINDINGS" -eq 0 ]; then
    echo "PASS — full git history is publication-clean (0 findings across all refs)."
    exit 0
fi
echo "BLOCKER — ${FINDINGS} finding(s). DO NOT push or make the repository public."
echo "Surface the finding(s) to a human. History rewrite is irreversible"
echo "(requires force-push) and is NEVER performed by this script."
exit 1
