cmake_minimum_required(VERSION 3.22.1)

project(poketrek LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# Tell mGBA we're building it embedded.
set(BUILD_SHARED OFF CACHE BOOL "" FORCE)
set(BUILD_STATIC ON CACHE BOOL "" FORCE)
set(BUILD_QT OFF CACHE BOOL "" FORCE)
set(BUILD_SDL OFF CACHE BOOL "" FORCE)
set(BUILD_LIBRETRO OFF CACHE BOOL "" FORCE)
set(BUILD_TEST OFF CACHE BOOL "" FORCE)
set(BUILD_PERF OFF CACHE BOOL "" FORCE)
set(BUILD_SUITE OFF CACHE BOOL "" FORCE)
set(DISABLE_FRONTENDS ON CACHE BOOL "" FORCE)
set(M_CORE_GBA ON CACHE BOOL "" FORCE)
set(M_CORE_GB OFF CACHE BOOL "" FORCE)
set(USE_FFMPEG OFF CACHE BOOL "" FORCE)
set(USE_PNG OFF CACHE BOOL "" FORCE)
set(USE_ZLIB ON CACHE BOOL "" FORCE)
set(USE_LIBZIP OFF CACHE BOOL "" FORCE)
set(USE_MINIZIP OFF CACHE BOOL "" FORCE)
set(USE_LZMA OFF CACHE BOOL "" FORCE)
set(USE_SQLITE3 OFF CACHE BOOL "" FORCE)
set(USE_DEBUGGERS OFF CACHE BOOL "" FORCE)
set(USE_GDB_STUB OFF CACHE BOOL "" FORCE)
set(USE_EDITLINE OFF CACHE BOOL "" FORCE)
set(USE_ELF OFF CACHE BOOL "" FORCE)

# Pull in mGBA. The vendored submodule lives at <repo>/third_party/mgba.
set(MGBA_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../third_party/mgba")
add_subdirectory("${MGBA_ROOT}" "${CMAKE_BINARY_DIR}/mgba" EXCLUDE_FROM_ALL)

# Vendored xdelta3 (decode-only subset) for on-device ROM patching.
# See third_party/xdelta3/README.poketrek.md. Config mirrors the host-side
# proof that reproduced leafgreen_J-K_2024.gba (CRC 0x4A38A8CB) byte-for-byte:
# no secondary compressors, no CLI, no regression suite. arm64-v8a and
# x86_64 are both LP64 so the SIZEOF_* values are correct for both ABIs.
set(XDELTA3_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/../../../../third_party/xdelta3")
add_library(xdelta3 STATIC "${XDELTA3_ROOT}/xdelta3.c")
target_include_directories(xdelta3 PUBLIC "${XDELTA3_ROOT}")
# PUBLIC, not PRIVATE: xdelta3.h derives usize_t/xoff_t from these at
# include time, so every consumer (jni_bridge.cpp) must see the identical
# values or the types mismatch across the JNI call.
target_compile_definitions(xdelta3 PUBLIC
    SIZEOF_SIZE_T=8
    SIZEOF_UNSIGNED_LONG_LONG=8
    SIZEOF_UNSIGNED_INT=4
    SIZEOF_UNSIGNED_LONG=8
    XD3_USE_LARGEFILE64=0
    SECONDARY_DJW=0
    SECONDARY_FGK=0
    SECONDARY_LZMA=0
    XD3_MAIN=0
    REGRESSION_TEST=0
    XD3_DEBUG=0
)
# Upstream third-party C; don't hold it to our -Wall -Wextra posture.
target_compile_options(xdelta3 PRIVATE -w)

add_library(poketrek SHARED
    jni_bridge.cpp
    movement_gate.cpp
)

target_include_directories(poketrek PRIVATE
    "${MGBA_ROOT}/include"
    "${MGBA_ROOT}/src"
)

# mGBA's static target is named `mgba` (CMake target). Link against it plus log/zlib.
target_link_libraries(poketrek PRIVATE
    mgba
    xdelta3
    android
    log
    z
)

target_compile_options(poketrek PRIVATE
    -Wall -Wextra -Wno-unused-parameter
    -ffunction-sections -fdata-sections
)

# Android 15+ on devices with 16KB pages requires .so segments aligned to 16KB.
# Without this the ELF loader falls back to compatibility mode and shows a warning.
target_link_options(poketrek PRIVATE
    "-Wl,-z,max-page-size=16384"
)
