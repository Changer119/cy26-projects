package com.phone2computer.transfer.data;

import static org.junit.Assert.assertEquals;

import com.phone2computer.transfer.core.UploadState;
import com.phone2computer.transfer.core.UploadTask;
import java.io.File;
import java.io.FileOutputStream;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public final class UploadJournalTest {
    @Rule
    public TemporaryFolder temporaryFolder = new TemporaryFolder();

    @Test
    public void restoresNewestStateForEveryTask() throws Exception {
        File file = temporaryFolder.newFile("tasks.journal");
        UploadJournal journal = new UploadJournal(file);
        UploadTask first = UploadTask.pending("1", "content://a", "a.jpg", 100L, 10L);
        UploadTask second = UploadTask.pending("2", "content://b", "b.mp4", 200L, 20L);

        journal.save(first);
        journal.save(second);
        journal.save(first.withRemote("http://mac/api/files/1", 50L));

        List<UploadTask> restored = new UploadJournal(file).list();
        assertEquals(2, restored.size());
        assertEquals(50L, restored.get(0).offset());
        assertEquals("2", restored.get(1).id());
    }

    @Test
    public void ignoresTruncatedTailRecord() throws Exception {
        File file = temporaryFolder.newFile("tasks.journal");
        UploadJournal journal = new UploadJournal(file);
        journal.save(UploadTask.pending("1", "content://a", "a.jpg", 100L, 10L));

        try (FileOutputStream output = new FileOutputStream(file, true)) {
            output.write(new byte[] {0, 0, 0, 20, 1, 2, 3});
        }

        assertEquals(1, new UploadJournal(file).list().size());
    }

    @Test
    public void retryFailedMovesOnlyFailedTasksBackToPending() throws Exception {
        File file = temporaryFolder.newFile("tasks.journal");
        UploadJournal journal = new UploadJournal(file);
        journal.save(
            UploadTask.pending("1", "content://a", "a.jpg", 100L, 10L)
                .withState(UploadState.FAILED, "网络中断")
        );
        journal.save(
            UploadTask.pending("2", "content://b", "b.jpg", 100L, 10L)
                .withState(UploadState.COMPLETED, "")
        );

        journal.retryFailed();

        assertEquals(UploadState.PENDING, journal.list().get(0).state());
        assertEquals(UploadState.COMPLETED, journal.list().get(1).state());
    }

    @Test
    public void pauseActiveLeavesCompletedTasksUntouched() throws Exception {
        File file = temporaryFolder.newFile("tasks.journal");
        UploadJournal journal = new UploadJournal(file);
        journal.save(UploadTask.pending("1", "content://a", "a.jpg", 100L, 10L));
        journal.save(
            UploadTask.pending("2", "content://b", "b.jpg", 100L, 10L)
                .withState(UploadState.UPLOADING, "")
        );
        journal.save(
            UploadTask.pending("3", "content://c", "c.jpg", 100L, 10L)
                .withState(UploadState.COMPLETED, "")
        );

        journal.pauseActive();

        assertEquals(UploadState.PAUSED, journal.list().get(0).state());
        assertEquals(UploadState.PAUSED, journal.list().get(1).state());
        assertEquals(UploadState.COMPLETED, journal.list().get(2).state());
    }

    @Test
    public void resumePausedMovesOnlyPausedTasksBackToPending() throws Exception {
        File file = temporaryFolder.newFile("tasks.journal");
        UploadJournal journal = new UploadJournal(file);
        journal.save(
            UploadTask.pending("1", "content://a", "a.jpg", 100L, 10L)
                .withState(UploadState.PAUSED, "")
        );
        journal.save(
            UploadTask.pending("2", "content://b", "b.jpg", 100L, 10L)
                .withState(UploadState.COMPLETED, "")
        );

        journal.resumePaused();

        assertEquals(UploadState.PENDING, journal.list().get(0).state());
        assertEquals(UploadState.COMPLETED, journal.list().get(1).state());
    }

    @Test
    public void twoInstancesCanAppendWithoutCorruptingRecords() throws Exception {
        File file = temporaryFolder.newFile("tasks.journal");
        UploadJournal first = new UploadJournal(file);
        UploadJournal second = new UploadJournal(file);
        CountDownLatch start = new CountDownLatch(1);
        ExecutorService workers = Executors.newFixedThreadPool(2);
        Future<?> firstWriter = workers.submit(() -> appendTasks(first, "a", start));
        Future<?> secondWriter = workers.submit(() -> appendTasks(second, "b", start));

        start.countDown();
        firstWriter.get();
        secondWriter.get();
        workers.shutdown();

        assertEquals(400, new UploadJournal(file).list().size());
    }

    private static void appendTasks(
        UploadJournal journal,
        String prefix,
        CountDownLatch start
    ) {
        try {
            start.await();
            for (int index = 0; index < 200; index++) {
                String id = prefix + index;
                journal.save(UploadTask.pending(id, "content://" + id, id + ".jpg", 1L, 1L));
            }
        } catch (Exception error) {
            throw new IllegalStateException(error);
        }
    }
}
