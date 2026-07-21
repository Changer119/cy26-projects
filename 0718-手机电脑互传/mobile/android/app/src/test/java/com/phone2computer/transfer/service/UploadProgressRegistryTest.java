package com.phone2computer.transfer.service;

import static org.junit.Assert.assertEquals;

import com.phone2computer.transfer.core.UploadTask;
import org.junit.After;
import org.junit.Test;

public final class UploadProgressRegistryTest {
    @After
    public void clearProgress() {
        UploadProgressRegistry.clearAll();
    }

    @Test
    public void combinesPersistedAndLiveProgressWithoutExceedingFileLength() {
        UploadTask task = UploadTask.pending("1", "content://video", "video.mp4", 100L, 1L)
            .withRemote("http://127.0.0.1/api/files/1", 20L);

        UploadProgressRegistry.update(task.id(), 65L);
        assertEquals(65L, UploadProgressRegistry.uploadedBytes(task));
        assertEquals(65, UploadProgressRegistry.progressPercent(task));

        UploadProgressRegistry.update(task.id(), 150L);
        assertEquals(100L, UploadProgressRegistry.uploadedBytes(task));
        assertEquals(100, UploadProgressRegistry.progressPercent(task));
    }

    @Test
    public void neverMovesLiveProgressBackwards() {
        UploadTask task = UploadTask.pending("1", "content://photo", "photo.jpg", 100L, 1L);

        UploadProgressRegistry.update(task.id(), 60L);
        UploadProgressRegistry.update(task.id(), 40L);

        assertEquals(60L, UploadProgressRegistry.uploadedBytes(task));
    }
}
