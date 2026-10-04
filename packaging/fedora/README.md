# Native Fedora source and build

The native build targets x86_64 Fedora 44 and 45. Prepare sources with network access,
then configure, compile and package without network access. No host packages or services
need to be changed. Python 3.12+, Git, and patch are needed for source preparation.

```
packaging/fedora/prepare-source.py /tmp/AppImageLauncher-source --ref HEAD
podman build --build-arg FEDORA_RELEASE=44 -t ail-fedora44 \
  -f /tmp/AppImageLauncher-source/ci/fedora/Containerfile /tmp/AppImageLauncher-source
podman run --rm --network=none -v /tmp/AppImageLauncher-source:/src:Z -w /src ail-fedora44 bash -euxc '
  export SOURCE_DATE_EPOCH=$(cat SOURCE_DATE_EPOCH)
  cmake -S . -B build -G Ninja -C packaging/fedora/native.cmake \
    -DCMAKE_INSTALL_PREFIX=/usr -DCMAKE_INSTALL_LIBDIR=lib64
  cmake --build build --parallel 4
  DESTDIR=/src/stage cmake --install build --component APPIMAGELAUNCHER
  DESTDIR=/src/stage cmake --install build --component APPIMAGELAUNCHER_CLI
'
```

Repeat with `FEDORA_RELEASE=45` and a separate source/build directory. Build the image
before the offline step. The prepared source is the image build context: the
Containerfile installs application BuildRequires directly from its committed RPM
spec using `dnf5 builddep`, after installing the spec-parsing and fixture tools.
Use a fresh output directory for `prepare-source.py`; it exports
the committed revision, not uncommitted work. `--cache DIR` reuses dependency Git objects.
`SOURCE_REVISION`, `SOURCE_DATE_EPOCH`, `cmake/GIT_COMMIT` and
`packaging/fedora/dependencies.json` retain version provenance without `.git` directories.
All dependency license files remain under `vendor/`. Local changes to these sources are
recorded in `packaging/fedora/patches/` and applied during preparation.

The prepared tree can be archived as an RPM Source0. For a reproducible gzip tar archive,
run before building (GNU tar):

```
SOURCE_DATE_EPOCH=$(cat /tmp/AppImageLauncher-source/SOURCE_DATE_EPOCH)
tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner \
  -C /tmp -cf - AppImageLauncher-source | gzip -n > AppImageLauncher-source.tar.gz
```

The initial CMake cache selects Fedora CPR/curl and squashfuse along with native Qt,
libarchive, Boost, libgcrypt, zlib and other system libraries. AppImageUpdate, zsync2,
libappimage, args and xdg-utils-cxx use immutable commits. Their private libraries retain
the upstream install component. Installing both named components avoids installing
unrelated dependency headers and tools while retaining `ail-cli`.

The preloaded interception libraries include a 32-bit C target; the binfmt interpreter
is linked statically and requires the static glibc/libstdc++ development packages.
Container builds prove compilation and userspace checks only. Graphical sessions,
host binfmt lifecycle and SELinux enforcement require the separate desktop acceptance
checklist. The Fedora package dependency graph can change as repositories are updated;
record the image digest and installed RPM versions alongside build results. Source
pinning does not assert byte-identical binaries across different distro package sets.
