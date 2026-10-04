# FileSystemWatcher behavior tests

These Linux tests exercise the watcher's public slots, directory query, and Qt
signals against real temporary directories and inotify events. They need CMake,
a C++17 compiler, and Qt 5 Core/Test development files (`cmake gcc-c++
qt5-qtbase-devel` on Fedora). No display server or AppImage dependency build is
required.

From the repository root, in your build environment:

```sh
cmake -S tests/fswatcher -B build-watcher -DCMAKE_BUILD_TYPE=Debug
cmake --build build-watcher --parallel
ctest --test-dir build-watcher --output-on-failure
```

For GCC/libstdc++ iterator diagnostics, additionally configure with
`-DCMAKE_CXX_FLAGS=-D_GLIBCXX_DEBUG`. The standalone target applies this flag
consistently to the test and watcher sources without mixing it into the
application's shared library interfaces.

The suite covers missing directories (including consecutive entries and the last
entry), removal of multiple watches, additions after the kernel removes a watch,
stale queued events and zero-name watch events, disappearance and reappearance,
file creation/rename/removal, directory signal payloads, and stop/restart. Async
assertions have bounded waits, and CTest has a 30-second timeout. One case can be
run directly, for example:

```sh
build-watcher/filesystemwatcher_tests missingDirectoriesAreFiltered
```

Container execution validates the watcher only; it does not establish graphical
session, host service, binfmt, or SELinux compatibility.
