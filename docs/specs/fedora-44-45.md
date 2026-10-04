# Fedora 44 and 45 native support

## Problem Statement

Fedora users need dependable AppImage desktop integration. Current Ubuntu-built packages bundle an incomplete Qt platform setup, have fragile helper paths and lifecycle handling, and the directory watcher contains invalid iterator handling. Neither Fedora 44 nor Fedora 45 has a verified native build and installed-package check in CI.

## Solution

Provide native x86_64 RPM builds for Fedora 44 and 45 using Fedora's Qt and supporting libraries. Fix confirmed watcher and helper defects, verify installed-package behavior, and document the remaining graphical and SELinux acceptance checks without claiming unperformed validation.

## User Stories

1. As a Fedora 44 user, I want an installable native RPM so that desktop integration uses my distribution's libraries.
2. As a Fedora 45 user, I want a separately built RPM so that newer system libraries are supported.
3. As a user, I want absent application directories to be ignored safely so that the daemon does not crash.
4. As a user, I want multiple missing directories handled correctly so that valid directories remain monitored.
5. As a user, I want directory removal to stop the old watch safely so that the daemon keeps running.
6. As a user, I want new directories monitored even when old watches disappear so that new AppImages are discovered.
7. As a user, I want file creation, movement and removal reported correctly so that integration stays current.
8. As a user, I want restarting the watcher to work so that configuration changes do not require restarting my session.
9. As a Wayland user, I want the matching Qt platform plugin installed so that launcher dialogs can open natively.
10. As a user, I want Update and Remove desktop actions to locate their helpers and libraries so that those actions work after installation.
11. As a user, I want RPM upgrades to preserve usable integration so that applications continue launching.
12. As a user, I want uninstall to remove interception cleanly so that AppImages can launch independently afterward.
13. As a maintainer, I want systemd units and binfmt configuration in their standard locations so that the system manages them correctly.
14. As a maintainer, I want pinned dependency sources and repeatable build commands so that builds can be reproduced.
15. As a maintainer, I want regression tests through public behavior so that internal refactoring does not invalidate the tests.
16. As a maintainer, I want both Fedora releases built and their RPMs checked in CI so that compatibility regressions are visible.
17. As a distributor, I want documented signing and COPR publication steps so that packages can meet Fedora 45's verification policy.
18. As a user, I want accurate validation notes so that container checks are not confused with desktop and SELinux certification.

## Implementation Decisions

- Maintain one integration branch based on upstream commit edd4ef418ece70112970b74408818e77b40264bd, targeting Fedora Workstation and KDE x86_64 on releases 44 and 45.
- Preserve Qt 5 and FUSE 2 compatibility; use native Qt, Wayland, curl and other available distribution libraries. Keep necessary AppImage-specific private libraries isolated.
- Add a native RPM build path alongside the existing upstream release pipeline. Respect GNU installation directories and Fedora RPM dependency generation.
- Pin fetched dependency revisions, arrange dependency sources before the RPM build when needed, and keep the package build reproducible and independently usable.
- Repair watcher iterator invalidation, removal-result handling and short-circuiting; handle kernel watch removal events without inventing paths or crashing.
- Correct helper resource and executable lookup where installed-package tests demonstrate failures. Preserve the existing public CLI and desktop-action behavior.
- Handle binfmt and user-service package lifecycle with Fedora-appropriate, upgrade-aware behavior. Do not enable or restart services on the developer's host during tests.
- Use separate Fedora 44/45 builds; investigate and fix demonstrated incompatibilities with current compilers, CMake and OpenSSL dependency chains.
- Document package signing; do not publish a production repository or claim a trusted release signing identity as part of this change.

## Testing Decisions

- The user approved these seams on 2026-10-04: watcher public API with real temporary directories; automated native builds and installed-RPM checks on Fedora 44 and 45; a separate GNOME/KDE Wayland and SELinux checklist with unrun tests explicitly marked.
- Introduce behavior-focused watcher regression coverage using the existing Qt public slots and signals, real filesystem events, and bounded waits. Avoid inspecting private maps or mocking internal collaborators.
- Use a red-before-green loop for demonstrated defects, one behavior at a time. No existing first-party test suite was found at the assessed base.
- Test the installed RPM's CLI and helper entry points, linked-library resolution, desktop files, declared runtime dependencies, service/config locations and package lifecycle in disposable containers where possible.
- Containers do not prove graphical session integration, host binfmt behavior or SELinux correctness. Record a manual VM/desktop checklist for those cases, including installation, reboot, upgrade, uninstall and a Fedora 44-to-45 upgrade.
- Report exact successful commands and any environmental limitations; do not equate a successful compile with complete AppImage compatibility.

## Out of Scope

- Qt 6 or FUSE 3 migration, ARM support, Fedora Atomic desktop packaging, unrelated distribution rewrites, and universal compatibility with every AppImage runtime.
- Production COPR deployment, release signing key creation, merging the final PR, or installation on the user's workstation.
- A new UI or changes to the intended integration/update/removal workflow.

## Further Notes

The previous assessment inspected source and upstream RPM metadata but did not complete a native build. Fedora 45 was beta at the time of assessment. Compatibility claims must be based on the new build/test results. Graphical and SELinux acceptance results may remain explicitly pending under the agreed testing scope.
