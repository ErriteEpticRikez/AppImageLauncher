# Native build validation, 2026-10-04

Fresh exports of source revision `fbe3980d19e2e3cc12b751699cfe984457517a02`
compiled successfully in separate Fedora 44 and 45 x86_64 Podman containers with
`--network=none`. The commands are in [README.md](README.md). Both named install
components were staged and `ail-cli --help` exited successfully. The Update helper
was explicitly enabled and built, and `ldd` resolved all its libraries.

| Build environment | Fedora 44 | Fedora 45 |
| --- | --- | --- |
| CMake | 4.3.0-1.fc44 | 4.3.0-5.fc45 |
| GCC | 16.2.1-2.fc44 | 16.2.1-2.fc45.1 |
| glibc | 2.43-9.fc44 | 2.44-2.fc45 |
| Qt base | 5.15.18-2.fc44 | 5.15.18-5.fc45 |
| CPR | 1.14.1-1.fc44 | 1.14.1-3.fc45 |
| curl | 8.18.0-10.fc44 | 8.21.0-6.fc45 |
| OpenSSL runtime | 3.5.9-1.fc44 | 4.0.3-1.fc45 |
| squashfuse | 0.5.2-6.fc44 | 0.5.2-7.fc45 |

The built `libbinfmt-bypass-preload_32bit.so` reports ELF32 via `readelf -h` in both
builds. The `binfmt-interpreter` has neither an INTERP program header nor NEEDED
dynamic entries, checked with `readelf -l` and `readelf -d`. Fedora 45's Update
helper resolves `libssl.so.4` through system CPR/curl; Fedora 44 resolves
`libssl.so.3`. No private curl or OpenSSL was compiled.

Observed failures and corresponding fixes:

- Fedora supplies versioned `lupdate-qt5` and `lrelease-qt5` names: find these
  before upstream's unversioned names.
- XdgUtils' ExternalProject had no Ninja byproduct rules: declare the two archives
  and use the pinned local source directory instead of its moving master branch.
- Global Qt autogen inserted C++ into the C preload library: disable autogen for
  those C targets, avoiding an unnecessary 32-bit C++ dependency.
- GCC's 32-bit link required `libatomic.i686`: declare the dependency explicitly.
- GCC 16 rejects zsync2's incompatible pointer types: explicitly expose URL arrays
  as read-only views and pass a correctly typed temporary to the decompression
  offset API before assigning the `off_t` result.
- Enabling the updater exposed its nlohmann-json and GPGME build requirements:
  include them in the image, and explicitly enable the updater in the native cache.

Source preparation was run twice at the same revision. Normalized GNU tar streams
(`--sort=name`, recorded epoch, numeric owner/group 0) had matching SHA-256
`6da89207b659d5675a438ba3d5b2a6192029f7252ea6a8a1fb2720bb3463da01`.
This demonstrates repeatable source exports; byte-identical binaries were not tested.

These are compilation, ELF, staged-library and CLI checks. They do not establish
installed-RPM lifecycle, graphical desktop integration or SELinux correctness.
Warnings remain in upstream dependencies and Qt deprecated APIs; none prevented
these builds. RPM and desktop acceptance results are recorded separately.
