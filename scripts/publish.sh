#!/usr/bin/env bash
# Publish chinese-scraper-utils to PyPI
# Usage: ./publish.sh <version>
# Requires: PYPI_TOKEN env var or .pypirc configured

set -euo pipefail

VERSION="${1:-}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$ ]]; then
  echo "ERROR: Invalid version format. Expected semver (e.g., 0.2.7 or 0.2.7-beta.1)"
  exit 1
fi

# Update version in pyproject.toml
sed -i "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# Build
pip install build twine
python -m build

# Check
twine check dist/*

echo ""
echo "Ready to publish v$VERSION to PyPI."
echo "Run: twine upload dist/*"
echo "Or use GitHub tag: git tag v$VERSION && git push origin v$VERSION"
