#!/usr/bin/env python3
"""Prepare a pinned source tree; this is the only network-enabled build step."""
import argparse
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile


def run(*args, **kwargs):
    return subprocess.check_output(args, **kwargs)


def export(repository, revision, destination):
    destination.mkdir(parents=True)
    with tempfile.TemporaryFile() as archive:
        subprocess.run(['git', '-C', str(repository), 'archive', revision], stdout=archive, check=True)
        archive.seek(0)
        with tarfile.open(fileobj=archive) as contents:
            contents.extractall(destination, filter='data')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path, help='new output directory (must not exist)')
    parser.add_argument('--ref', default='HEAD', help='AppImageLauncher Git revision')
    parser.add_argument('--cache', type=Path, default=Path.home() / '.cache/appimagelauncher-sources')
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[2]
    destination = args.destination.resolve()
    if destination.exists():
        parser.error('destination already exists')
    commit = run('git', '-C', str(repository), 'rev-parse', args.ref, text=True).strip()
    epoch = run('git', '-C', str(repository), 'show', '-s', '--format=%ct', commit, text=True).strip()
    export(repository, commit, destination)
    (destination / 'cmake/GIT_COMMIT').write_text(commit[:7] + '\n')
    (destination / 'SOURCE_DATE_EPOCH').write_text(epoch + '\n')
    manifest = json.loads((destination / 'packaging/fedora/dependencies.json').read_text())
    args.cache.mkdir(parents=True, exist_ok=True)
    for dependency in manifest:
        name, revision = dependency['name'], dependency['commit']
        checkout = args.cache.resolve() / name
        if not checkout.exists():
            subprocess.run(['git', 'clone', '--bare', dependency['url'], str(checkout)], check=True)
        if subprocess.run(['git', '-C', str(checkout), 'cat-file', '-e', revision + '^{commit}'],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
            subprocess.run(['git', '-C', str(checkout), 'fetch', dependency['url'], revision], check=True)
        export(checkout, revision, destination / 'vendor' / name)
        patch = destination / 'packaging/fedora/patches' / (name + '.patch')
        if patch.exists():
            subprocess.run(['patch', '-p1', '-i', str(patch)], cwd=destination / 'vendor' / name, check=True)
    # License files remain in each vendor source tree; retain the immutable graph with the archive.
    (destination / 'SOURCE_REVISION').write_text(commit + '\n')
    print(destination)


if __name__ == '__main__':
    main()
