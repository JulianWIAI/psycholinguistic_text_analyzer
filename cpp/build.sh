#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# build.sh  —  Compile the _somatic_core pybind11 extension
#
# Usage (from project root):
#   bash cpp/build.sh
#
# The compiled .so is placed in the project root so that
#   import _somatic_core
# works without any sys.path manipulation.
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$SCRIPT_DIR/build"

echo "▸ Installing pybind11 if missing …"
pip install pybind11 --quiet

echo "▸ Configuring …"
cmake -B "$BUILD_DIR" \
      -S "$SCRIPT_DIR" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_INSTALL_PREFIX="$PROJECT_ROOT"

echo "▸ Building …"
cmake --build "$BUILD_DIR" --config Release -j"$(nproc 2>/dev/null || sysctl -n hw.logicalcpu 2>/dev/null || echo 4)"

echo "▸ Installing .so into project root …"
cmake --install "$BUILD_DIR"

echo ""
echo "✓ Build complete. Test with:"
echo "  python -c \"import _somatic_core; print(_somatic_core.analyze('hello world'))\""
