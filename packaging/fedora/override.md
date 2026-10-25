# Temporarily bypass AppImageLauncher

The Fedora RPM installs `appimage-launcher-override` in `/usr/bin`:

```bash
appimage-launcher-override status
sudo appimage-launcher-override off
/path/to/application.AppImage
sudo appimage-launcher-override on
```

Run the AppImage as your normal user. The toggle requires root and affects all
users and AppImages. You can turn interception back on after the application
has started. Existing application processes are unaffected.

Only AppImageLauncher kernel handlers are changed; unrelated binary formats
and persistent configuration are left alone. Rebooting, reinstalling/upgrading
AppImageLauncher, or re-registering handlers can restore interception. `on`
enables all matching registered handlers, including previously disabled ones.
If no matching handlers are registered, the command reports that and changes
nothing. It does not register missing handlers.

`APPIMAGELAUNCHER_DISABLE=1` only suppresses the integration dialog and still
uses the launcher bypass component. See the [upstream explanation](https://github.com/TheAssassin/AppImageLauncher/discussions/679)
and [kernel interface documentation](https://docs.kernel.org/admin-guide/binfmt-misc.html).
