cmake_minimum_required(VERSION 3.15)
project(_somatic_core CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# ── Find Python & pybind11 ───────────────────────────────────────────────────
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG QUIET)

if(NOT pybind11_FOUND)
    execute_process(
        COMMAND ${Python3_EXECUTABLE} -m pybind11 --cmakedir
        OUTPUT_VARIABLE PYBIND11_CMAKE_DIR
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    if(PYBIND11_CMAKE_DIR)
        list(APPEND CMAKE_PREFIX_PATH "${PYBIND11_CMAKE_DIR}")
        find_package(pybind11 CONFIG REQUIRED)
    else()
        message(FATAL_ERROR "pybind11 not found. Install with: pip install pybind11")
    endif()
endif()

# ── Source files ─────────────────────────────────────────────────────────────
# Each logical concern is its own translation unit (modular design):
#   letter_table.cpp — A-Z value + category lookup table
#   fft.cpp          — Radix-2 Cooley-Tukey FFT (standard library only)
#   somatic_analyzer.cpp — main per-window analysis + global envelope
#   bindings.cpp     — pybind11 Python module glue

pybind11_add_module(_somatic_core
    letter_table.cpp
    fft.cpp
    somatic_analyzer.cpp
    bindings.cpp
)

target_include_directories(_somatic_core PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

# Optimization flags
if(MSVC)
    target_compile_options(_somatic_core PRIVATE /O2 /W3)
else()
    target_compile_options(_somatic_core PRIVATE -O3 -Wall -Wextra)
endif()

# ── Install the .so into the project root so `import _somatic_core` works ───
install(TARGETS _somatic_core
    LIBRARY DESTINATION ${CMAKE_SOURCE_DIR}/..
    RUNTIME DESTINATION ${CMAKE_SOURCE_DIR}/..
)
