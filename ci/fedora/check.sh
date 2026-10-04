#!/usr/bin/env bash
# Host-side orchestration; all package installation happens in disposable containers.
set -euo pipefail
release=${1:?usage: check.sh FEDORA_RELEASE OUTPUT_DIR}
case "$release" in 44|45) ;; *) echo 'Supported Fedora releases: 44, 45' >&2; exit 2 ;; esac
output=$(realpath -m "${2:?output directory required}")
if [[ -e "$output" ]]; then
    echo "Output directory must not already exist: $output" >&2
    exit 2
fi
engine=${CONTAINER_ENGINE:-podman}
repository=$(git -C "$(dirname "${BASH_SOURCE[0]}")/../.." rev-parse --show-toplevel)
mkdir -p "$output"
exec > >(tee "$output/validation.log") 2>&1
scratch=$(mktemp -d)
trap 'rm -rf "$scratch"' EXIT
builder="localhost/appimagelauncher-fedora${release}-builder:validation"
base="registry.fedoraproject.org/fedora:${release}"
export BUILD_JOBS=${BUILD_JOBS:-2}

# Preparation may fetch only the dependency revisions pinned in the committed tree.
python3 "$repository/packaging/fedora/prepare-source.py" "$scratch/source" --ref HEAD
cp "$scratch/source/SOURCE_REVISION" "$scratch/source/SOURCE_DATE_EPOCH" "$output/"
cp "$scratch/source/packaging/fedora/dependencies.json" "$output/"
"$engine" build --pull --build-arg "FEDORA_RELEASE=$release" -t "$builder" \
    -f "$repository/ci/fedora/Containerfile" "$repository/ci/fedora" 2>&1 | tee "$output/builder.log"
"$engine" image inspect "$builder" > "$output/builder-image.json"
"$engine" pull "$base"
"$engine" image inspect "$base" > "$output/runtime-image.json"

# A separate standalone build exercises real filesystem events with iterator checks.
"$engine" run --rm --network=none -v "$scratch/source:/src:ro,Z" "$builder" bash -euxc '
    cmake -S /src/tests/fswatcher -B /tmp/watcher-build -DCMAKE_BUILD_TYPE=Debug \
        -DCMAKE_CXX_FLAGS=-D_GLIBCXX_DEBUG
    cmake --build /tmp/watcher-build --parallel 2
    ctest --test-dir /tmp/watcher-build --output-on-failure
' 2>&1 | tee "$output/watcher.log"

# Build two releases to exercise a real upgrade, including both packages' scriptlets.
# Source0 and SRPM include dependency sources; rpmbuild cannot access the network.
for build_release in 1 2; do
    if [[ "$build_release" == 1 ]]; then destination=previous; else destination=current; fi
    "$engine" run --rm --network=none -e BUILD_JOBS -e "BUILD_RELEASE=$build_release" \
        -v "$scratch/source:/src:ro,Z" -v "$output:/out:Z" "$builder" \
        bash /src/packaging/fedora/build-rpm.sh /src "/out/$destination" \
        2>&1 | tee "$output/rpmbuild-$build_release.log"
done
"$engine" run --rm --network=none -v "$scratch/source:/src:ro,Z" \
    -v "$output:/out:Z" "$builder" python3 /src/packaging/fedora/make-fixtures.py /out/fixtures

# The runtime container gets only RPMs, fixtures and tests, never builder libraries.
mkdir "$scratch/runtime-tests"
cp "$scratch/source/packaging/fedora/"{test-rpm.sh,smoke-installed.py} "$scratch/runtime-tests/"
"$engine" run --rm -v "$output/previous/RPMS:/previous:ro,Z" \
    -v "$output/current/RPMS:/current:ro,Z" -v "$output/fixtures:/fixtures:ro,Z" \
    -v "$scratch/runtime-tests:/tests:ro,Z" "$base" bash -euxc '
        bash /tests/test-rpm.sh /previous/x86_64/appimagelauncher-*.rpm \
            /current/x86_64/appimagelauncher-*.rpm /fixtures /tests
    ' 2>&1 | tee "$output/installed-rpm.log"
