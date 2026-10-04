#!/usr/bin/env bash
# Run only in a fresh disposable Fedora runtime container, never on a workstation.
set -euo pipefail
if [ ! -f /run/.containerenv ] && [ ! -f /.dockerenv ]; then
    echo "This script must run inside a disposable container" >&2
    exit 1
fi
first_rpm=$(realpath "${1:?usage: test-rpm.sh RPM_RELEASE_1 RPM_RELEASE_2 FIXTURE_DIR TEST_SCRIPT_DIR}")
second_rpm=$(realpath "${2:?higher-release RPM required}")
fixtures=$(realpath "${3:?fixture directory required}")
tests=$(realpath "${4:?directory containing smoke-installed.py required}")
# Tools for test orchestration only; GUI and library dependencies come from the RPM.
dnf -y --setopt=install_weak_deps=False install python3 desktop-file-utils glibc-common
# This per-command exception applies only to local, unsigned test artifacts.
# Repository dependencies retain their normal signature checking policy.
dnf -y --setopt=install_weak_deps=False --setopt=localpkg_gpgcheck=0 install "$first_rpm"
first_version=$(rpm -q --qf '%{EVR}' appimagelauncher)
python3 "$tests/smoke-installed.py" "$fixtures"
dnf -y --setopt=install_weak_deps=False --setopt=localpkg_gpgcheck=0 upgrade "$second_rpm"
second_version=$(rpm -q --qf '%{EVR}' appimagelauncher)
test "$first_version" != "$second_version"
python3 "$tests/smoke-installed.py" "$fixtures"
dnf -y remove appimagelauncher
if rpm -q appimagelauncher; then
    echo 'Package remains installed after erase' >&2
    exit 1
fi
for path in /usr/bin/ail-cli /usr/bin/AppImageLauncher /usr/lib64/appimagelauncher \
            /usr/lib/systemd/user/appimagelauncherd.service /usr/lib/binfmt.d/appimagelauncher.conf; do
    test ! -e "$path"
done
printf 'PASS: RPM install, version upgrade (%s -> %s), final erase in a container.\n' "$first_version" "$second_version"
printf 'Live binfmt registrations, graphical sessions and SELinux acceptance were not tested.\n'
