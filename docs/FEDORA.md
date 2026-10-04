# Fedora 44 and 45

This native x86_64 RPM path uses Fedora Qt 5 (including the Wayland platform
plugin), FUSE 2, curl, CPR and squashfuse. AppImage-specific libraries live in
`/usr/lib64/appimagelauncher`; Qt and its plugins come from Fedora packages.
The native path is separate from upstream's Ubuntu-based release packages.
It does not establish compatibility with every AppImage runtime.

## Build and automated checks

Use a disposable Linux build environment with Git, Python 3.12+, `patch`, GNU tar,
and Podman or Docker. The commands install packages inside containers. They do not
install the RPM or manage services on the host. Commit source changes first:
source preparation exports the requested Git revision, not uncommitted files.
From the repository root:

```sh
CONTAINER_ENGINE=podman BUILD_JOBS=2 bash ci/fedora/check.sh 44 /tmp/ail-fedora44-results
CONTAINER_ENGINE=podman BUILD_JOBS=2 bash ci/fedora/check.sh 45 /tmp/ail-fedora45-results
```

Each output directory must be new. On a Docker host, set `CONTAINER_ENGINE=docker`.
The runner performs these steps independently for each release:

1. Prepare the committed source tree and pinned dependency revisions with network
   access using `packaging/fedora/prepare-source.py`. Build the Fedora toolchain
   image from the exported `ci/fedora/Containerfile` with `FEDORA_RELEASE=44` or `45`,
   using the committed source export as the build context. The image derives its
   application dependencies from that export's RPM spec using `dnf5 builddep`.
2. Run the standalone watcher tests in a network-disabled container, with
   libstdc++ debug iterator checks and bounded waits on real filesystem events.
3. Run `packaging/fedora/build-rpm.sh PREPARED_SOURCE OUTPUT_DIR` inside that
   builder with `--network=none`. The source archive and SRPM contain all required
   vendor sources; CMake's Fedora cache disables dependency fetching. Build releases
   1 and 2 provide a real package-upgrade transaction.
4. Generate deterministic integration fixtures, then install the RPM with its
   dependencies in a fresh Fedora base container. Run the installed-package
   smoke checks, upgrade to release 2, and repeat the smoke checks without mounting
   source/build libraries into that container.
5. Erase the package and check that its CLI, private library directory, user unit
   and binfmt configuration were removed.

The runtime container requires network access for Fedora dependency installation.
CI's unsigned local RPM is installed with a transaction-scoped signature-checking
exception inside that disposable container. This is not a release signing or
end-user installation procedure. Containers are not privileged and do not mount
the host's home, systemd runtime or binfmt registration filesystem.

`current/RPMS/x86_64/` and `current/SRPMS/` contain the binary and source packages. Logs include
`builder.log`, `watcher.log`, `rpmbuild-1.log`, `rpmbuild-2.log`, `installed-rpm.log` and the combined
`validation.log`. Image inspection JSON, the installed build package list,
`SOURCE_REVISION`, `SOURCE_DATE_EPOCH`, dependency manifest and `SHA256SUMS` record
provenance. `previous/RPMS/` retains the older upgrade-test package. Keep these
with the artifacts. Fedora repositories and container tags
can change; pinned dependency commits alone do not imply byte-identical binaries
across different toolchain package sets. See the [source preparation details](../packaging/fedora/README.md).

The [Fedora workflow](../.github/workflows/fedora.yml) runs both releases on
x86_64, grants only repository read permission, and uploads RPMs, SRPMs, source
archives, metadata and available logs even after a failed check. It does not
publish a release, push container images, or need signing credentials. The
legacy workflow is restricted to `TheAssassin/AppImageLauncher` because its build
script publishes to that repository's hard-coded GHCR namespace.

## Validation status

Recorded on 2026-10-04. The full local container runner passed for both releases
at `ff438744ecffaeace601f534e2d0ec2a2c88adea`, including the final review fixes.
The hosted matrix also passed on the earlier integration revision `0f9f326`:
[GitHub Actions run 37180402258](https://github.com/ErriteEpticRikez/AppImageLauncher/actions/runs/37180402258).
See [PR checks](https://github.com/ErriteEpticRikez/AppImageLauncher/pull/6/checks)
for hosted results on subsequent revisions. A configured workflow alone is not
evidence of a completed run.

| Check | Fedora 44 | Fedora 45 |
| --- | --- | --- |
| Standalone watcher tests, real filesystem events, `_GLIBCXX_DEBUG` | PASS: 1/1 CTest suite, 13 QtTest results | PASS: 1/1 CTest suite, 13 QtTest results |
| Native source build with network disabled | PASS | PASS |
| Staged `ail-cli --help`, helper linkage and static interpreter checks | PASS | PASS |
| Final installed-RPM smoke, upgrade and erase checks | PASS | PASS |
| GNOME/KDE Wayland, SELinux enforcing and host lifecycle checks below | NOT RUN | NOT RUN |
| Remote Fedora Actions matrix at `0f9f326` (linked above) | PASS | PASS |

Native build evidence and exact commands are in
[native validation notes](../packaging/fedora/native-validation.md). The watcher
suite covers absent directories, rapid recreation with consumed or pending kernel
events, removal of replacement watches, watch removal, kernel-removed watches,
stale queued events, additions, file creation/movement/removal and restart. Its
[standalone instructions](../tests/fswatcher/README.md) are independent of the
application dependency build. Headless helper startup does not prove a completed
Update or Remove action or a usable Wayland dialog.

The final local runs used the commands above with output directories
`/tmp/ail-fedora44-final-results` and `/tmp/ail-fedora45-final-results`; both exited
0. Each contains build logs, installed-package logs, provenance, RPMs and SRPMs.
The package tests installed release 1, upgraded to release 2, verified retained
user integration, then erased the package. These paths are local evidence, not
permanent artifact hosting. GitHub run artifacts provide downloadable copies of
that run's packages and logs during the configured retention period.

[Independent review results](FEDORA-REVIEW.md) record the findings and fixes.

## Desktop and lifecycle acceptance — NOT RUN

Run this checklist in disposable Fedora 44 and Fedora 45 x86_64 VMs, separately
with GNOME Wayland and KDE Plasma Wayland and SELinux enforcing. Record the VM
image, desktop/session versions, package NEVRA and checksum, AppImage fixtures,
commands, exit status, screenshots and relevant journal/AVC output. Leave each
item pending until its outcome is recorded.

- [ ] **Install and launch:** verify the package signature, install the matching
  RPM with dependencies, and confirm Qt loads the native Wayland plugin. Integrate
  a known FUSE 2 AppImage from a path containing spaces; check menu entry, icon,
  launcher prompt, configured destination, and launch from the desktop.
- [ ] **Watcher and restart:** create, move and remove AppImages in watched
  directories; remove and recreate a watched directory and change configuration.
  Restart the user daemon and verify events continue without duplicate entries.
- [ ] **Update and Remove:** use an AppImage with valid update information to open
  and complete Update, observing spinner and result. Use Remove from the desktop
  menu and confirm the intended AppImage and integration entries disappear.
  Check missing/invalid update metadata reports a useful failure.
- [ ] **SELinux:** keep enforcing mode enabled throughout launch, integration,
  Update and Remove; inspect `journalctl --user`, the system journal and
  `ausearch -m AVC,USER_AVC -ts recent`. Record any denial and its exact trigger.
- [ ] **Reboot:** confirm integration and launch still work after reboot and
  login, with the user service following Fedora preset/enablement policy.
- [ ] **RPM upgrade:** install an older build, integrate an AppImage, then upgrade
  to a higher package release. Confirm user service handling, retained settings
  and launch. Verify both `appimage-type1` and `appimage-type2` binfmt registrations
  refer to the current interpreter and use `F`; verify an unrelated registration
  remains untouched. Exercise launch after the old interpreter inode is replaced.
- [ ] **Uninstall:** erase the package and verify only its two binfmt registrations
  disappear, unrelated formats remain, its user unit is gone, and AppImages can
  launch independently. Record what happens to previously integrated desktop
  entries and user data. Repeat installation after erase.
- [ ] **Fedora 44 → 45 upgrade:** start with the Fedora 44 package and integrated
  AppImages, perform a supported distro upgrade in the VM, install the Fedora 45
  build, reboot and repeat launch, Update, Remove, watcher and SELinux checks.

Container package transactions cannot prove kernel binfmt refresh, logged-in
user service restarts, graphical behavior, or SELinux policy compatibility.

## Signing and optional COPR publication

The artifacts from this workflow are development packages. Fedora's
[signature enforcement change for Fedora 45](https://fedoraproject.org/wiki/Changes/Enforcing_signature_checking_by_default)
requires verifiable signatures by default. Use a maintained release signing
identity for distributed packages; this change creates no production key and
publishes no repository.

With an existing signing key on a dedicated signing machine, use
[`rpmsign`](https://rpm.org/docs/6.1.x/man/rpmsign.1), substituting its fingerprint
and the exact artifact filenames:

```sh
rpmsign --addsign --key-id YOUR_SIGNING_KEY_FINGERPRINT appimagelauncher-VERSION.x86_64.rpm
rpmsign --addsign --key-id YOUR_SIGNING_KEY_FINGERPRINT appimagelauncher-VERSION.src.rpm
rpmkeys --checksig appimagelauncher-VERSION.x86_64.rpm
```

The verification machine must trust the matching public key. Publish the public
key and fingerprint through a trusted channel, and verify them before importing
the key and installing packages. For isolated local development, RPM also
provides `/usr/lib/rpm/rpm-setup-autosign`; follow its generated key-import
instructions in that environment. Local autosigning is not a production identity.

An optional future COPR workflow uses the populated SRPM, so builds need no Git
fetch in `%build`. Authenticate with `copr-cli` on the maintainer's machine and
confirm both requested chroots are available before creating a project:

```sh
copr-cli create appimagelauncher-fedora --chroot fedora-44-x86_64 --chroot fedora-45-x86_64
copr-cli build appimagelauncher-fedora /path/to/appimagelauncher-VERSION.src.rpm
```

COPR signs its own build outputs. Review each chroot's logs, signatures and
installed-package results before advertising a repository. Follow the
[COPR user documentation](https://docs.copr.fedorainfracloud.org/user_documentation.html)
for account/token setup and SRPM submission. These are documented future actions;
no COPR project, release signing key, or production repository was created.
