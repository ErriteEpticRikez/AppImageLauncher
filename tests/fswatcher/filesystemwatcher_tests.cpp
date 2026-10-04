#include <QFile>
#include <QSignalSpy>
#include <QTemporaryDir>
#include <QtTest>

#include "filesystemwatcher.h"

Q_DECLARE_METATYPE(QDirSet)

using appimagelauncher::daemon::FileSystemWatcher;

class FileSystemWatcherTests : public QObject {
    Q_OBJECT

private:
    static bool writeFile(const QString& path) {
        QFile file(path);
        return file.open(QIODevice::WriteOnly) && file.write("AppImage test") == 13;
    }

private slots:
    void initTestCase() {
        qRegisterMetaType<QDirSet>();
    }

    void missingDirectoryAtEndIsIgnored() {
        QTemporaryDir temporary;
        QVERIFY(temporary.isValid());
        FileSystemWatcher watcher;
        QVERIFY(watcher.updateWatchedDirectories({QDir(temporary.filePath("missing"))}));
        QVERIFY(watcher.directories().empty());
        QVERIFY(watcher.startWatching());
        QVERIFY(watcher.stopWatching());
    }

    void disappearedDirectoryCanBeWatchedAgain() {
        QTemporaryDir temporary;
        QVERIFY(temporary.isValid());
        QDir root(temporary.path());
        QVERIFY(root.mkdir("applications"));
        const QDir applications(root.filePath("applications"));
        FileSystemWatcher watcher(applications);
        QSignalSpy changed(&watcher, &FileSystemWatcher::fileChanged);
        QSignalSpy added(&watcher, &FileSystemWatcher::newDirectoriesToWatch);
        QSignalSpy disappeared(&watcher, &FileSystemWatcher::directoriesToWatchDisappeared);
        QVERIFY(watcher.startWatching());
        QVERIFY(root.rmdir("applications"));
        watcher.readEvents();
        QCOMPARE(changed.count(), 0);
        QVERIFY(watcher.updateWatchedDirectories({applications}));
        QVERIFY(watcher.directories().empty());
        QCOMPARE(disappeared.count(), 1);
        QVERIFY(qvariant_cast<QDirSet>(disappeared.at(0).at(0)) == QDirSet{applications});
        added.clear();

        QVERIFY(root.mkdir("applications"));
        QVERIFY(watcher.updateWatchedDirectories({applications}));
        QCOMPARE(added.count(), 1);
        QVERIFY(qvariant_cast<QDirSet>(added.at(0).at(0)) == QDirSet{applications});
        const auto path = applications.filePath("returned.AppImage");
        QVERIFY(writeFile(path));
        QTRY_COMPARE_WITH_TIMEOUT(changed.count(), 1, 1000);
        QCOMPARE(changed.at(0).at(0).toString(), path);
        QVERIFY(watcher.stopWatching());
    }

    void watcherCanBeStoppedAndRestarted() {
        QTemporaryDir temporary;
        QVERIFY(temporary.isValid());
        FileSystemWatcher watcher(QDir(temporary.path()));
        QSignalSpy changed(&watcher, &FileSystemWatcher::fileChanged);
        QVERIFY(watcher.startWatching());
        QVERIFY(watcher.startWatching());
        QVERIFY(watcher.stopWatching());
        QVERIFY(watcher.stopWatching());
        QVERIFY(writeFile(temporary.filePath("while-stopped.AppImage")));
        QTest::qWait(200);
        QCOMPARE(changed.count(), 0);

        QVERIFY(watcher.startWatching());
        const auto path = temporary.filePath("after-restart.AppImage");
        QVERIFY(writeFile(path));
        QTRY_COMPARE_WITH_TIMEOUT(changed.count(), 1, 1000);
        QCOMPARE(changed.at(0).at(0).toString(), path);
        QVERIFY(watcher.stopWatching());
    }

    void fileCreationMovementAndRemovalAreReported() {
        QTemporaryDir temporary;
        QVERIFY(temporary.isValid());
        FileSystemWatcher watcher(QDir(temporary.path()));
        QSignalSpy changed(&watcher, &FileSystemWatcher::fileChanged);
        QSignalSpy removed(&watcher, &FileSystemWatcher::fileRemoved);
        QVERIFY(watcher.startWatching());
        const auto original = temporary.filePath("original.AppImage");
        const auto moved = temporary.filePath("moved.AppImage");
        QVERIFY(writeFile(original));
        QTRY_COMPARE_WITH_TIMEOUT(changed.count(), 1, 1000);
        QCOMPARE(changed.takeFirst().at(0).toString(), original);

        QVERIFY(QFile::rename(original, moved));
        QTRY_COMPARE_WITH_TIMEOUT(removed.count(), 1, 1000);
        QCOMPARE(removed.takeFirst().at(0).toString(), original);
        QCOMPARE(changed.count(), 1);
        QCOMPARE(changed.takeFirst().at(0).toString(), moved);

        QVERIFY(QFile::remove(moved));
        QTRY_COMPARE_WITH_TIMEOUT(removed.count(), 1, 1000);
        QCOMPARE(removed.at(0).at(0).toString(), moved);
        QVERIFY(watcher.stopWatching());
    }

    void queuedEventsFromRemovedWatchesAreIgnored() {
        QTemporaryDir temporary;
        QVERIFY(temporary.isValid());
        FileSystemWatcher watcher(QDir(temporary.path()));
        QSignalSpy changed(&watcher, &FileSystemWatcher::fileChanged);
        QSignalSpy removed(&watcher, &FileSystemWatcher::fileRemoved);
        QVERIFY(watcher.startWatching());
        QVERIFY(writeFile(temporary.filePath("queued.AppImage")));
        QVERIFY(watcher.updateWatchedDirectories({}));

        // Read a queued file event and the kernel's zero-name IN_IGNORED event.
        watcher.readEvents();
        QCOMPARE(changed.count(), 0);
        QCOMPARE(removed.count(), 0);
        QVERIFY(watcher.stopWatching());
    }

    void newDirectoriesAreWatchedAfterOldDirectoryDisappears() {
        QTemporaryDir temporary;
        QVERIFY(temporary.isValid());
        QDir root(temporary.path());
        QVERIFY(root.mkdir("old"));
        QVERIFY(root.mkdir("new"));
        FileSystemWatcher watcher(QDir(root.filePath("old")));
        QSignalSpy changed(&watcher, &FileSystemWatcher::fileChanged);
        QVERIFY(watcher.startWatching());
        QVERIFY(root.rmdir("old"));

        // The kernel has already removed the old watch; additions must still proceed.
        const bool updated = watcher.updateWatchedDirectories({QDir(root.filePath("new"))});
        const auto path = root.filePath("new/new.AppImage");
        QVERIFY(writeFile(path));
        QTRY_COMPARE_WITH_TIMEOUT(changed.count(), 1, 1000);
        QCOMPARE(changed.at(0).at(0).toString(), path);
        QVERIFY(updated);
        QVERIFY(watcher.stopWatching());
    }

    void removedDirectoriesStopReportingChanges() {
        QTemporaryDir temporary;
        QVERIFY(temporary.isValid());
        QDir root(temporary.path());
        QVERIFY(root.mkdir("first"));
        QVERIFY(root.mkdir("second"));
        FileSystemWatcher watcher(QDirSet{QDir(root.filePath("first")), QDir(root.filePath("second"))});
        QSignalSpy changed(&watcher, &FileSystemWatcher::fileChanged);
        QVERIFY(watcher.startWatching());

        QVERIFY(watcher.updateWatchedDirectories({}));
        QVERIFY(writeFile(root.filePath("first/one.AppImage")));
        QVERIFY(writeFile(root.filePath("second/two.AppImage")));
        QTest::qWait(200);
        QCOMPARE(changed.count(), 0);
        QVERIFY(watcher.stopWatching());
    }

    void missingDirectoriesAreFiltered() {
        QTemporaryDir temporary;
        QVERIFY(temporary.isValid());
        QDir root(temporary.path());
        QVERIFY(root.mkdir("z-existing"));
        const QDir existing(root.filePath("z-existing"));
        FileSystemWatcher watcher;

        QVERIFY(watcher.updateWatchedDirectories({
            QDir(root.filePath("a-missing")), QDir(root.filePath("b-missing")), existing,
        }));
        QVERIFY(watcher.directories() == QDirSet{existing});
    }
};

QTEST_GUILESS_MAIN(FileSystemWatcherTests)
#include "filesystemwatcher_tests.moc"
