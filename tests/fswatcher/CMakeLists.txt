cmake_minimum_required(VERSION 3.16)
project(FileSystemWatcherTests LANGUAGES CXX)

# Standalone entry point: these tests need no AppImage build dependencies.
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_AUTOMOC ON)
find_package(Qt5 REQUIRED COMPONENTS Core Test)
enable_testing()

add_executable(filesystemwatcher_tests
    filesystemwatcher_tests.cpp
    ../../src/fswatcher/filesystemwatcher.cpp
    ../../src/fswatcher/filesystemwatcher.h
    ../../src/shared/types.cpp
)
target_include_directories(filesystemwatcher_tests PRIVATE ../../src/fswatcher ../../src/shared)
target_link_libraries(filesystemwatcher_tests PRIVATE Qt5::Core Qt5::Test)
add_test(NAME filesystemwatcher COMMAND filesystemwatcher_tests)
set_tests_properties(filesystemwatcher PROPERTIES TIMEOUT 30)
