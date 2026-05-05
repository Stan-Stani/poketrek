cmake_minimum_required(VERSION 3.16)
project(mgba_capture C)

set(CMAKE_C_STANDARD 11)
set(CMAKE_BUILD_TYPE Release)

# Locate the libmgba install (brew --HEAD prefers HEAD; fall back to 0.10.5).
foreach(prefix
    /opt/homebrew/Cellar/mgba/HEAD-b19b557_2
    /opt/homebrew/Cellar/mgba/0.10.5_2
    /opt/homebrew)
    if(EXISTS ${prefix}/include/mgba/core/core.h AND
       EXISTS ${prefix}/lib/libmgba.dylib)
        set(MGBA_PREFIX ${prefix})
        break()
    endif()
endforeach()

if(NOT MGBA_PREFIX)
    message(FATAL_ERROR "libmgba not found. Run: brew install --HEAD mgba")
endif()
message(STATUS "Using libmgba from: ${MGBA_PREFIX}")

add_executable(mgba_capture capture.c)
target_include_directories(mgba_capture PRIVATE ${MGBA_PREFIX}/include)
target_link_directories(mgba_capture PRIVATE ${MGBA_PREFIX}/lib)
target_link_libraries(mgba_capture PRIVATE mgba m)
target_compile_definitions(mgba_capture PRIVATE
    M_CORE_GBA=1
    USE_LIBZIP=0
)
# Make rpath relative so the binary finds libmgba even if homebrew dir changes.
set_target_properties(mgba_capture PROPERTIES
    INSTALL_RPATH "${MGBA_PREFIX}/lib"
    BUILD_WITH_INSTALL_RPATH TRUE)
