"""
setup.py — psycho_core pybind11 extension build script.

Builds the C++20 BPV orthographic engine + compare engine as a Python
extension module without requiring cmake.  Uses the standard setuptools
Extension mechanism driven by pybind11's header-only install.

Usage (from cpp_core/ directory):
    pip install pybind11 --quiet          # once, if not already installed
    pip install . --no-build-isolation    # compile + install into active env
    # or for in-place development build:
    python setup.py build_ext --inplace
"""

import sys
import os
from setuptools import setup, Extension

try:
    import pybind11
except ImportError:
    print("ERROR: pybind11 is required. Run: pip install pybind11", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Detect Python include path (needed for the extension header)
# ---------------------------------------------------------------------------
import sysconfig
py_include = sysconfig.get_path("include")

# ---------------------------------------------------------------------------
# Compiler flags
# ---------------------------------------------------------------------------
# Apple Clang 17 on macOS Sequoia supports C++20 (including std::jthread).
# -fvisibility=hidden matches pybind11's recommendation to keep symbol table clean.
extra_compile = [
    "-std=c++20",
    "-O3",
    "-fvisibility=hidden",
    "-Wall",
    "-Wextra",
    "-Wno-unused-parameter",
]

# On macOS, target the current SDK so headers resolve correctly.
if sys.platform == "darwin":
    # Suppress Apple's deprecation warnings for older POSIX APIs used internally.
    extra_compile += ["-Wno-deprecated-declarations"]
    # Use libc++ (Clang's stdlib) — already the default on macOS, but be explicit.
    extra_compile += ["-stdlib=libc++"]

extra_link = []
if sys.platform == "darwin":
    extra_link += ["-stdlib=libc++"]

# ---------------------------------------------------------------------------
# Extension definition
# ---------------------------------------------------------------------------
sources = [
    "src/pipeline.cpp",
    "src/compare_engine.cpp",
    "src/window_engine.cpp",
    "src/micro_analyzer.cpp",
    "src/thread_pool.cpp",
    "src/bindings.cpp",
]

psycho_core = Extension(
    name="psycho_core",
    sources=sources,
    include_dirs=[
        "include",
        pybind11.get_include(),
        py_include,
    ],
    extra_compile_args=extra_compile,
    extra_link_args=extra_link,
    language="c++",
)

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
setup(
    name="psycho_core",
    version="3.1.0",
    description="PsychoLinguistic Analysis Engine — compiled BPV + Compare core",
    ext_modules=[psycho_core],
)
