# Fedora 44/45 implementation review

The integration changes were reviewed against upstream base
`edd4ef418ece70112970b74408818e77b40264bd` and the
[approved specification](specs/fedora-44-45.md). Independent Standards and Spec
reviews were repeated after fixes at
`704ae0bad85f31366ae7e021e807021bcdc51ca7`, merged as `ff438744`.

## Standards

No hard documented-standard violations were found. The initial review raised one
nonblocking Duplicated Code / Shotgun Surgery concern: application build
dependencies were enumerated independently in the container and RPM specification.
The container now installs bootstrap and fixture tools separately, then derives
application dependencies with `dnf5 builddep` from the committed RPM specification.
The build context and documentation use the same prepared source export.

Follow-up review found no remaining Standards findings. Watcher tests use public
slots and signals, real temporary directories, bounded asynchronous assertions,
and a CTest timeout, consistent with the documented testing choices.

## Spec

The initial review confirmed one P2 defect: removing and recreating a watched
directory before reconciliation could leave that path permanently unmonitored.
This violated the required disappearance/reappearance behavior. Reconciliation
now reasserts watches for requested paths and retires obsolete descriptors for
replaced inodes.

Three regression cases cover recreation after consuming removal events,
recreation while removal events are pending, and subsequent removal from the
requested watch set before pending events are consumed. The last case also
caught and fixed a stale descriptor that could otherwise keep emitting events
after removal.

Follow-up review found no remaining Spec findings. The reviewer independently
rebuilt and ran the complete watcher suite with debug iterator checks in Fedora
44 and 45 containers: 13 QtTest results passed and none failed on each release.
The native build and dependency consolidation remain within the approved scope.

The approved scope permits the graphical, live binfmt, SELinux and distro-upgrade
checks to remain explicitly unrun. See [Fedora validation status](FEDORA.md) for
package and CI evidence and the separate manual checklist.

Remaining findings: Standards 0 (no outstanding severity); Spec 0 (no outstanding severity).
