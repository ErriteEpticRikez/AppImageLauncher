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
upgrade_home=$(mktemp -d)
trap 'rm -rf "$upgrade_home"' EXIT
export HOME="$upgrade_home" XDG_CONFIG_HOME="$upgrade_home/config" XDG_DATA_HOME="$upgrade_home/data"
mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$upgrade_home/Applications"
printf '[AppImageLauncher]\ndestination = %s/Applications\nenable_daemon = false\n' "$upgrade_home" > "$XDG_CONFIG_HOME/appimagelauncher.cfg"
cp "$fixtures/Fixture Update.AppImage" "$upgrade_home/Upgrade Fixture.AppImage"
ail-cli integrate "$upgrade_home/Upgrade Fixture.AppImage"
integrated=$(find "$upgrade_home/Applications" -name '*.AppImage' -print -quit)
desktop=$(find "$XDG_DATA_HOME/applications" -name 'appimagekit_*.desktop' -print -quit)
test -f "$integrated" && test -f "$desktop"
first_version=$(rpm -q --qf '%{EVR}' appimagelauncher)
python3 "$tests/smoke-installed.py" "$fixtures"
dnf -y --setopt=install_weak_deps=False --setopt=localpkg_gpgcheck=0 upgrade "$second_rpm"
second_version=$(rpm -q --qf '%{EVR}' appimagelauncher)
test "$first_version" != "$second_version"
# The user's existing integration must survive replacement of the package payload.
test -f "$integrated" && test -f "$desktop"
ail-cli integrate "$integrated"
desktop-file-validate "$desktop"
python3 "$tests/smoke-installed.py" "$fixtures"
dnf -y remove appimagelauncher
# Package erasure must not remove the user's AppImage or its direct desktop entry.
test -f "$integrated" && test -f "$desktop"
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
