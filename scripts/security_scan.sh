#!/bin/bash
# Security scan — run before any release
# QP-22: SBOM generation + vulnerability scanning
set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DATE_TAG="$(date +%Y%m%d)"
SECURITY_DIR="$REPO_ROOT/docs/security"

mkdir -p "$SECURITY_DIR"

echo "=== pip-audit (Python vulnerabilities) ==="
if command -v pip-audit &>/dev/null; then
    pip-audit -r "$REPO_ROOT/api/requirements.txt" --format=json \
        > "$SECURITY_DIR/pip-audit-$DATE_TAG.json" 2>&1 \
        && echo "pip-audit: complete — results in docs/security/pip-audit-$DATE_TAG.json" \
        || echo "pip-audit: finished with warnings (see output file)"
else
    echo "pip-audit not installed — skipping (install: pip install pip-audit)"
fi

echo ""
echo "=== Generate Python SBOM ==="
pip list --format=json > "$SECURITY_DIR/python-sbom-$DATE_TAG.json"
echo "Python SBOM written: docs/security/python-sbom-$DATE_TAG.json"

echo ""
echo "=== Node audit ==="
if [ -d "$REPO_ROOT/quantum-portal-web" ]; then
    cd "$REPO_ROOT/quantum-portal-web"
    npm audit --json > "$SECURITY_DIR/npm-audit-$DATE_TAG.json" 2>&1 || true
    echo "npm audit: results in docs/security/npm-audit-$DATE_TAG.json"
    cd "$REPO_ROOT"
else
    echo "quantum-portal-web not found — skipping npm audit"
fi

echo ""
echo "=== Check for secrets in staged files ==="
STAGED=$(git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null || true)
if [ -n "$STAGED" ]; then
    HITS=$(echo "$STAGED" | xargs grep -l "password\|secret\|api_key\|private_key" 2>/dev/null || true)
    if [ -n "$HITS" ]; then
        echo "WARNING: possible secrets in staged files:"
        echo "$HITS"
        exit 1
    else
        echo "No obvious secrets found in staged files"
    fi
else
    echo "No staged files to check"
fi

echo ""
echo "=== Scan complete ==="
