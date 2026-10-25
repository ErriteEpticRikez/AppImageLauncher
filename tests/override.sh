#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/../bin/appimage-launcher-override"

fixture=$(mktemp -d)
trap 'rm -rf "$fixture"' EXIT
BINFMT_DIR=$fixture

[[ $(main status) == 'No AppImageLauncher kernel handlers are registered; no changes made.' ]]
printf 'enabled\n' > "$fixture/status"
printf 'enabled\ninterpreter /usr/bin/qemu-aarch64-static\n' > "$fixture/unrelated"
printf 'enabled\ninterpreter /usr/bin/AppImageLauncher\n' > "$fixture/appimage-type1"
printf 'disabled\ninterpreter /usr/lib64/appimagelauncher/binfmt-bypass\n' > "$fixture/appimage-type2"
expected=$'appimage-type1: enabled\nappimage-type2: disabled'
[[ $(main status) == "$expected" ]]

if (( EUID == 0 )); then
    main off > /dev/null
    [[ $(cat "$fixture/appimage-type1") == 0 ]]
    [[ $(cat "$fixture/appimage-type2") == 0 ]]
    # Real procfs retains handler metadata after writes; restore the fixture.
    printf 'disabled\ninterpreter /usr/bin/AppImageLauncher\n' > "$fixture/appimage-type1"
    printf 'disabled\ninterpreter /usr/lib64/appimagelauncher/binfmt-bypass\n' > "$fixture/appimage-type2"
    main on > /dev/null
    [[ $(cat "$fixture/appimage-type1") == 1 ]]
    [[ $(cat "$fixture/appimage-type2") == 1 ]]
else
    if main off > /dev/null 2>&1; then exit 1; fi
    if main on > /dev/null 2>&1; then exit 1; fi
    [[ $(main status) == "$expected" ]]
fi
[[ $(cat "$fixture/status") == enabled ]]
[[ $(cat "$fixture/unrelated") == $'enabled\ninterpreter /usr/bin/qemu-aarch64-static' ]]
if main invalid > /dev/null 2>&1; then exit 1; fi
if main off extra > /dev/null 2>&1; then exit 1; fi
printf 'Override checks passed.\n'
