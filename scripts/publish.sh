#!/bin/bash
# Publish chinese-scraper-utils to PyPI
# Usage: ./publish.sh <version>
# Requires: PYPI_TOKEN env var or .pypirc configured

set -e

VERSION=${1:?"Usage: ./publish.sh <version> (e.g., 0.2.0)"}

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
