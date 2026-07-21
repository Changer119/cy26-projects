package com.phone2computer.transfer.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import org.junit.Test;

public final class UploadTaskTest {
    @Test
    public void computesProgressFromPersistedOffset() {
        UploadTask task = UploadTask.pending("1", "content://photo/1", "a.jpg", 200L, 123L)
            .withRemote("http://mac/api/files/abc", 50L)
            .withState(UploadState.UPLOADING, "");

        assertEquals(25, task.progressPercent());
        assertEquals(50L, task.offset());
    }

    @Test
    public void rejectsOffsetPastFileLength() {
        UploadTask task = UploadTask.pending("1", "content://photo/1", "a.jpg", 100L, 123L);

        assertThrows(
            IllegalArgumentException.class,
            () -> task.withRemote("http://mac/api/files/abc", 101L)
        );
    }

    @Test
    public void zeroByteFileReportsCompleteProgress() {
        UploadTask task = UploadTask.pending("1", "content://photo/1", "empty.jpg", 0L, 123L);

        assertEquals(100, task.progressPercent());
    }
}
