"""
Alternative build path via setuptools + pybind11.

Usage (from project root):
    pip install pybind11
    python cpp/setup.py build_ext --inplace

The compiled .so lands in the project root so `import _somatic_core` works
without any sys.path manipulation.
"""

import os
import sys
from setuptools import setup, Extension

try:
    import pybind11
    pybind11_include = pybind11.get_include()
except ImportError:
    print("ERROR: pybind11 not found.  Run: pip install pybind11", file=sys.stderr)
    sys.exit(1)

cpp_dir = os.path.dirname(os.path.abspath(__file__))

sources = [
    os.path.join(cpp_dir, "letter_table.cpp"),
    os.path.join(cpp_dir, "fft.cpp"),
    os.path.join(cpp_dir, "somatic_analyzer.cpp"),
    os.path.join(cpp_dir, "bindings.cpp"),
]

ext = Extension(
    "_somatic_core",
    sources=sources,
    include_dirs=[cpp_dir, pybind11_include],
    extra_compile_args=["-O3", "-std=c++17"],
    language="c++",
)

setup(
    name="_somatic_core",
    version="2.0.0",
    description="Somatic/Archetypal Cipher C++ core with FFT spectral analysis",
    ext_modules=[ext],
)
