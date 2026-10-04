#!/usr/bin/env python3
"""Check the installed RPM through its CLI, helpers and generated desktop files.

Run only in a disposable Fedora runtime container. Fixture directory is produced
by make-fixtures.py in the builder. No host mounts, binfmt writes or systemctl.
"""
import argparse
import configparser
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def run(*command, expected=0):
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, timeout=30)
    print('$', ' '.join(map(str, command)), '\n', result.stdout, flush=True)
    assert result.returncode == expected, (command, result.returncode, result.stdout)
    return result.stdout


def helper_dialog(helper, fixture):
    process = subprocess.Popen([str(helper), str(fixture)], text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT)
    try:
        output, _ = process.communicate(timeout=3)
        raise AssertionError(f'{helper} closed before its dialog could remain open: {output}')
    except subprocess.TimeoutExpired:
        process.terminate()
        output, _ = process.communicate(timeout=5)
    print(f'$ {helper} {fixture} (terminated after observing startup)\n{output}', flush=True)
    for failure in ('No such file or directory', 'module "', 'is not installed',
                    'could not be found', 'fallback icons could not be loaded',
                    'Error loading', 'error while loading shared libraries'):
        assert failure not in output, output


def desktop(path):
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path)
    run('desktop-file-validate', str(path))
    return parser


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixtures', type=Path)
    args = parser.parse_args()
    private = Path('/usr/lib64/appimagelauncher')
    files = run('rpm', '-ql', 'appimagelauncher').splitlines()
    for required in ('/usr/bin/ail-cli', '/usr/lib/systemd/user/appimagelauncherd.service',
                     '/usr/lib/binfmt.d/appimagelauncher.conf', str(private / 'update'),
                     str(private / 'remove'), str(private / 'binfmt-interpreter')):
        assert required in files, required
    assert not any('/opt/' in path or '/plugins/' in path for path in files), files
    dependencies = run('rpm', '-q', '--requires', 'appimagelauncher')
    for required in ('qt5-qtwayland', 'qt5-qtquickcontrols2', 'qt5-qtsvg', 'fuse-libs'):
        assert required in dependencies, required
    run('rpm', '-q', '--scripts', 'appimagelauncher')
    run('rpm', '-q', '--whatprovides', 'libfuse.so.2()(64bit)')
    run('rpm', '-q', 'fuse')
    for filename in files:
        path = Path(filename)
        if not path.is_file() or path.is_symlink():
            continue
        with path.open('rb') as stream:
            is_elf = stream.read(4) == b'\x7fELF'
        if is_elf:
            result = subprocess.run(['ldd', filename], text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=10)
            assert 'not found' not in result.stdout, (filename, result.stdout)
            assert result.returncode == 0 or 'not a dynamic executable' in result.stdout or 'statically linked' in result.stdout, result.stdout
    for entry in Path('/usr/share/applications').glob('*appimagelauncher*.desktop'):
        run('desktop-file-validate', str(entry))
    with tempfile.TemporaryDirectory(prefix='ail-installed-') as temporary:
        home = Path(temporary)
        for name in ('config', 'data', 'cache', 'runtime', 'Applications'):
            (home / name).mkdir(mode=0o700)
        os.environ.update(HOME=str(home), XDG_CONFIG_HOME=str(home / 'config'),
                          XDG_DATA_HOME=str(home / 'data'), XDG_CACHE_HOME=str(home / 'cache'),
                          XDG_RUNTIME_DIR=str(home / 'runtime'), QT_QPA_PLATFORM='offscreen',
                          QT_QUICK_BACKEND='software', LANG='C.UTF-8')
        (home / 'config/appimagelauncher.cfg').write_text(
            f'[AppImageLauncher]\ndestination = {home}/Applications\nask_to_move = false\nenable_daemon = false\n')
        run('ail-cli', '--help')
        run('ail-cli', '--version')
        run('ail-cli', 'integrate', expected=3)
        for helper in ('remove', 'update'):
            output = run(str(private / helper), '--help')
            assert 'could not be found' not in output, output
        fixture = home / 'Fixture Update.AppImage'
        shutil.copyfile(args.fixtures / fixture.name, fixture)
        run('ail-cli', 'would-integrate', str(fixture))
        run('ail-cli', 'integrate', str(fixture))
        integrated = list((home / 'Applications').glob('*.AppImage'))
        assert len(integrated) == 1 and not fixture.exists(), integrated
        entries = list((home / 'data/applications').glob('appimagekit_*.desktop'))
        assert len(entries) == 1, entries
        entry = desktop(entries[0])
        for action, helper in [('Remove', 'remove'), ('Update', 'update')]:
            section = entry[f'Desktop Action AppImageLauncher-{action}-AppImage']
            assert section['Exec'] == f'{private}/{helper} "{integrated[0]}"', dict(section)
            assert os.access(private / helper, os.X_OK)
        assert str(integrated[0]) in entry['Desktop Entry']['Exec'], dict(entry['Desktop Entry'])
        icons = list((home / 'data/icons').rglob('*.svg'))
        assert icons, 'No integrated icon'
        run('ail-cli', 'integrate', str(integrated[0]))
        assert list((home / 'data/applications').glob('appimagekit_*.desktop')) == entries
        run('ail-cli', 'unintegrate', str(integrated[0]))
        assert integrated[0].exists() and not entries[0].exists()
        # Empty update info avoids any external request while constructing both dialogs.
        no_update = home / 'Fixture No Update.AppImage'
        shutil.copyfile(args.fixtures / no_update.name, no_update)
        run('ail-cli', 'integrate', str(no_update))
        entries = list((home / 'data/applications').glob('appimagekit_*.desktop'))
        assert len(entries) == 1, entries
        entry = desktop(entries[0])
        assert 'Desktop Action AppImageLauncher-Update-AppImage' not in entry
        no_update = next(path for path in (home / 'Applications').glob('*.AppImage') if path != integrated[0])
        helper_dialog(private / 'remove', no_update)
        helper_dialog(private / 'update', no_update)
    print('PASS: installed RPM CLI, desktop actions, loader and helper resource startup. '
          'Graphical completion, active binfmt lifecycle and SELinux remain separate checks.')


if __name__ == '__main__':
    main()
