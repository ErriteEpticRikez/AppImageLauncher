#!/usr/bin/env bash
# Run INSIDE the Fedora builder container; prepared sources must be network-free.
set -euo pipefail
source_dir=$(realpath "${1:?usage: build-rpm.sh PREPARED_SOURCE OUTPUT_DIR}")
output_dir=$(realpath -m "${2:?output directory required}")
mkdir -p "$output_dir"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
export SOURCE_DATE_EPOCH=$(cat "$source_dir/SOURCE_DATE_EPOCH")
# Normalize the top-level name regardless of the caller's preparation directory.
tar --sort=name --mtime="@$SOURCE_DATE_EPOCH" --owner=0 --group=0 --numeric-owner \
    --exclude='./build' --exclude='./stage' --transform='s,^\.,AppImageLauncher-source,' \
    -C "$source_dir" -cf - . | gzip -n > "$output_dir/SOURCES/AppImageLauncher-source.tar.gz"
cp "$source_dir/packaging/fedora/appimagelauncher.spec" "$output_dir/SPECS/"
rpmbuild -ba --define "_topdir $output_dir" --define "_smp_build_ncpus ${BUILD_JOBS:-4}" \
    ${BUILD_RELEASE:+--define "build_release $BUILD_RELEASE"} \
    "$output_dir/SPECS/appimagelauncher.spec"
rpm -qa | sort > "$output_dir/build-packages.txt"
cp "$source_dir/SOURCE_REVISION" "$source_dir/SOURCE_DATE_EPOCH" "$output_dir/"
cp "$source_dir/packaging/fedora/dependencies.json" "$output_dir/"
sha256sum "$output_dir"/RPMS/*/*.rpm "$output_dir"/SRPMS/*.rpm > "$output_dir/SHA256SUMS"
