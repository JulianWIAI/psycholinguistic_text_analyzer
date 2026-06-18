# CMakeLists.txt — psycho_core shared library
# ============================================
# Builds the C++20 BPV orthographic engine as a Python extension module
# (pybind11 shared library) that the FastAPI backend imports at runtime.
#
# Requirements:
#   - CMake  >= 3.21
#   - C++20-capable compiler (GCC >= 11, Clang >= 13, MSVC >= 19.29 / VS 2019 16.11)
#   - Python >= 3.9  with development headers
#
# Quick build (from this directory):
#   cmake -B build -DCMAKE_BUILD_TYPE=Release
#   cmake --build build --config Release -j
#
# The compiled module (psycho_core.*.so / psycho_core.*.pyd) is placed in
# build/ and can be copied next to main.py for `import psycho_core`.
#
# Optional: install to the project root automatically:
#   cmake --install build --prefix ..

cmake_minimum_required(VERSION 3.21)
project(psycho_core
    VERSION     1.0.0
    DESCRIPTION "PsychoLinguistic Analysis Engine — compiled BPV core"
    LANGUAGES   CXX
)

# ---------------------------------------------------------------------------
# C++20 — required for std::jthread, std::stop_token, designated initialisers
# ---------------------------------------------------------------------------
set(CMAKE_CXX_STANDARD          20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS        OFF)   # use -std=c++20, not -std=gnu++20

# ---------------------------------------------------------------------------
# pybind11  (fetched automatically if not found locally)
# ---------------------------------------------------------------------------
# To use a system-installed copy instead, set:
#   cmake -B build -Dpybind11_DIR=/path/to/pybind11/share/cmake/pybind11
find_package(pybind11 QUIET)

if(NOT pybind11_FOUND)
    message(STATUS "pybind11 not found locally — fetching from GitHub")
    include(FetchContent)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG        v2.13.6
        GIT_SHALLOW    TRUE
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# ---------------------------------------------------------------------------
# Source files
# ---------------------------------------------------------------------------
set(PSYCHO_SOURCES
    src/window_engine.cpp
    src/micro_analyzer.cpp
    src/thread_pool.cpp
    src/bindings.cpp
)

# ---------------------------------------------------------------------------
# Build target — pybind11 extension module (shared library with Python suffix)
# ---------------------------------------------------------------------------
pybind11_add_module(psycho_core ${PSYCHO_SOURCES})

target_include_directories(psycho_core
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# ---------------------------------------------------------------------------
# Compiler optimisation flags
# ---------------------------------------------------------------------------
if(MSVC)
    # MSVC: /O2 = maximise speed, /GL = whole-program optimisation (LTO),
    # /arch:AVX2 = best vectorisation on modern x86-64 (equivalent of -march=native).
    # /W3 = standard warnings.
    target_compile_options(psycho_core PRIVATE
        /O2
        /GL
        /arch:AVX2
        /W3
        /wd4996   # suppress deprecation warnings from pybind11 internals
    )
    target_link_options(psycho_core PRIVATE
        /LTCG     # link-time code generation matches /GL
    )
else()
    # GCC / Clang
    target_compile_options(psycho_core PRIVATE
        -O3
        -march=native    # tune for the build machine's CPU
        -flto            # link-time optimisation
        -Wall
        -Wextra
        -Wno-unused-parameter
    )
    target_link_options(psycho_core PRIVATE
        -flto
    )
endif()

# ---------------------------------------------------------------------------
# Preprocessor defines
# ---------------------------------------------------------------------------
target_compile_definitions(psycho_core PRIVATE
    PSYCHO_VERSION="${PROJECT_VERSION}"
)

# ---------------------------------------------------------------------------
# Install: copy the built module to the project root (one level up)
# ---------------------------------------------------------------------------
install(
    TARGETS psycho_core
    LIBRARY DESTINATION "${CMAKE_SOURCE_DIR}/.."   # → project root on Unix
    RUNTIME DESTINATION "${CMAKE_SOURCE_DIR}/.."   # → project root on Windows (.pyd)
)

# ---------------------------------------------------------------------------
# Status summary
# ---------------------------------------------------------------------------
message(STATUS "-------------------------------------------------------")
message(STATUS "  psycho_core  v${PROJECT_VERSION}")
message(STATUS "  Build type : ${CMAKE_BUILD_TYPE}")
message(STATUS "  Compiler   : ${CMAKE_CXX_COMPILER_ID} ${CMAKE_CXX_COMPILER_VERSION}")
message(STATUS "  C++ std    : C++${CMAKE_CXX_STANDARD}")
message(STATUS "  Python     : ${Python_EXECUTABLE}")
message(STATUS "-------------------------------------------------------")
