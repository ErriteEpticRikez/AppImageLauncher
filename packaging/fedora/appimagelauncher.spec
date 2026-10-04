%global private_libdir %{_libdir}/appimagelauncher
%global debug_package %{nil}
# Private implementation libraries must not become public RPM capabilities.
%global __provides_exclude_from ^%{private_libdir}/.*$
%global __requires_exclude ^libappimage(update(-qt)?)?\\.so.*$

Name:           appimagelauncher
Version:        3.0.0~beta2
Release:        %{?build_release}%{!?build_release:1}%{?dist}
Summary:        Integrate AppImages with the desktop
# License texts and embedded-code notices are shipped under %%license.
License:        MIT AND LicenseRef-Artistic-2.0beta4 AND Zlib AND LicenseRef-Fedora-Public-Domain AND LGPL-2.1-or-later AND (GPL-3.0-or-later WITH GCC-exception-3.1)
URL:            https://github.com/TheAssassin/AppImageLauncher
Source0:        AppImageLauncher-source.tar.gz
ExclusiveArch:  x86_64

BuildRequires:  cmake gcc gcc-c++ make ninja-build git
BuildRequires:  glibc-devel(x86-32) glibc-static libstdc++-static libatomic(x86-32)
BuildRequires:  fuse-devel glib2-devel cairo-devel libbsd-devel
BuildRequires:  qt5-qtbase-devel qt5-qtdeclarative-devel qt5-qttools-devel
BuildRequires:  qt5-qtquickcontrols2 qt5-qtwayland
BuildRequires:  libcurl-devel cpr-devel squashfuse-devel
BuildRequires:  automake autoconf libtool xxd desktop-file-utils
BuildRequires:  libarchive-devel boost-devel librsvg2-devel librsvg2-tools
BuildRequires:  xz-devel libgcrypt-devel libzstd-devel patchelf nlohmann-json-devel gpgme-devel
BuildRequires:  systemd-rpm-macros
# Runtime QML imports/platform plugins are invisible to ELF dependency generation.
Requires:       qt5-qtquickcontrols2 qt5-qtdeclarative qt5-qtwayland qt5-qtsvg
Requires:       desktop-file-utils shared-mime-info xdg-utils
# Legacy type-2 runtimes load FUSE 2 themselves, outside our ELF dependency graph.
Requires:       fuse fuse-libs%{?_isa}
%systemd_requires
Provides:       bundled(libappimage) = 1.0.3
Provides:       bundled(zsync2) = 2.0.0~alpha1
Provides:       bundled(zlib) = 1.2.1.1

%description
AppImageLauncher integrates AppImages into desktop application menus and supplies
update and removal actions. This native Fedora build uses distribution Qt, curl,
CPR and squashfuse, with AppImage-specific libraries kept in a private directory.
Pinned dependency revisions are recorded in the installed dependencies.json.

%prep
%autosetup -n AppImageLauncher-source

%build
export SOURCE_DATE_EPOCH=$(cat SOURCE_DATE_EPOCH)
cmake -S . -B build -G Ninja -C packaging/fedora/native.cmake \
    -DCMAKE_INSTALL_PREFIX=%{_prefix} -DCMAKE_INSTALL_BINDIR=bin \
    -DCMAKE_INSTALL_LIBDIR=lib64 -DCMAKE_INSTALL_DATADIR=share \
    -DENABLE_UPDATE_HELPER=ON
cmake --build build --parallel %{_smp_build_ncpus}

%install
DESTDIR=%{buildroot} cmake --install build --component APPIMAGELAUNCHER
DESTDIR=%{buildroot} cmake --install build --component APPIMAGELAUNCHER_CLI
# Keep distinct license files rather than overwriting several LICENSE.txt files.
mkdir -p license-notices
cp LICENSE.txt license-notices/AppImageLauncher.txt
cp vendor/appimageupdate/LICENSE.txt license-notices/AppImageUpdate.txt
cp vendor/libappimage/LICENSE* license-notices/libappimage.txt
cp vendor/xdgutils/LICENSE* license-notices/xdg-utils-cxx.txt
cp vendor/args/LICENSE* license-notices/args.txt
cp vendor/zsync2/COPYING license-notices/zsync2.txt
cp vendor/zsync2/lib/zlib/README license-notices/zlib.txt
cp vendor/zsync2/lib/librcksum/md4.c license-notices/md4.c
cp vendor/zsync2/lib/libzsync/sha1.c license-notices/sha1.c
cp vendor/libappimage/src/libappimage_hashlib/md5.c license-notices/md5.c
# The static binfmt interpreter incorporates Fedora C/C++ runtime code.
cp -a /usr/share/licenses/glibc license-notices/glibc
cp -a /usr/share/licenses/libgcc license-notices/gcc-runtime
rpm -q --qf '%%{NAME} %%{EVR} %%{SOURCERPM}\n' glibc-static libstdc++-static > static-runtime-sources.txt

%check
desktop-file-validate %{buildroot}%{_datadir}/applications/*.desktop
test -x %{buildroot}%{_bindir}/ail-cli
test -x %{buildroot}%{private_libdir}/update
test -x %{buildroot}%{private_libdir}/remove

%post
%systemd_user_post appimagelauncherd.service
# Replaces only these formats and refreshes the F-pinned interpreter on upgrades.
%binfmt_apply appimagelauncher.conf

%preun
%systemd_user_preun appimagelauncherd.service
if [ "$1" -eq 0 ]; then
    for name in appimage-type1 appimage-type2; do
        entry=/proc/sys/fs/binfmt_misc/$name
        if [ -w "$entry" ] && grep -q '^interpreter %{private_libdir}/binfmt-interpreter$' "$entry"; then
            echo -1 > "$entry" || :
        fi
    done
fi

%postun
%systemd_user_postun_with_restart appimagelauncherd.service

%files
%license license-notices/
%doc README.md packaging/fedora/dependencies.json SOURCE_REVISION SOURCE_DATE_EPOCH static-runtime-sources.txt
%{_bindir}/AppImageLauncher
%{_bindir}/AppImageLauncherSettings
%{_bindir}/appimagelauncherd
%{_bindir}/ail-cli
%{private_libdir}/
%{_userunitdir}/appimagelauncherd.service
%{_binfmtdir}/appimagelauncher.conf
%{_datadir}/appimagelauncher/
%{_datadir}/applications/*.desktop
%{_datadir}/icons/hicolor/*/apps/AppImageLauncher.*
%{_datadir}/mime/packages/*
%{_mandir}/man1/AppImageLauncher.1*
