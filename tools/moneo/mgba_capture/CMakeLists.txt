cmake_minimum_required(VERSION 3.16)
project(mgba_capture C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_BUILD_TYPE Release)

# Prefer the vendored mGBA 0.10.5 built locally (brew HEAD bottle is currently
# broken on macOS arm64 — segfaults inside core->init()).
set(MGBA_VENDOR "${CMAKE_SOURCE_DIR}/../../../third_party/mgba")
set(MGBA_VENDOR_BUILD "${MGBA_VENDOR}/build-mac")

if(EXISTS "${MGBA_VENDOR_BUILD}/libmgba.dylib")
    set(MGBA_INCLUDE "${MGBA_VENDOR}/include")
    set(MGBA_LIBDIR  "${MGBA_VENDOR_BUILD}")
    message(STATUS "Using vendored libmgba 0.10.5: ${MGBA_LIBDIR}")
elseif(EXISTS "/opt/homebrew/Cellar/mgba/HEAD-b19b557_2/lib/libmgba.dylib")
    set(MGBA_INCLUDE "/opt/homebrew/Cellar/mgba/HEAD-b19b557_2/include")
    set(MGBA_LIBDIR  "/opt/homebrew/Cellar/mgba/HEAD-b19b557_2/lib")
    message(STATUS "Falling back to brew HEAD libmgba (may segfault).")
else()
    message(FATAL_ERROR "libmgba not found. Build third_party/mgba/build-mac first.")
endif()

add_executable(mgba_capture capture.c)
target_include_directories(mgba_capture PRIVATE ${MGBA_INCLUDE})
target_link_directories(mgba_capture PRIVATE ${MGBA_LIBDIR})
target_link_libraries(mgba_capture PRIVATE mgba m)
target_compile_definitions(mgba_capture PRIVATE
    M_CORE_GBA=1
    USE_LIBZIP=0
)
set_target_properties(mgba_capture PROPERTIES
    INSTALL_RPATH "${MGBA_LIBDIR}"
    BUILD_WITH_INSTALL_RPATH TRUE)
