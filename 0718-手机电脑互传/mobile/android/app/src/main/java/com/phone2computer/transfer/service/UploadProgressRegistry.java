package com.phone2computer.transfer.service;

import com.phone2computer.transfer.core.UploadState;
import com.phone2computer.transfer.core.UploadTask;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

public final class UploadProgressRegistry {
    private static final ConcurrentMap<String, Long> LIVE_BYTES = new ConcurrentHashMap<>();

    private UploadProgressRegistry() {
    }

    public static void update(String taskId, long uploadedBytes) {
        LIVE_BYTES.merge(taskId, Math.max(0L, uploadedBytes), Math::max);
    }

    public static long uploadedBytes(UploadTask task) {
        if (task.state() == UploadState.COMPLETED) {
            return task.length();
        }
        long liveBytes = LIVE_BYTES.getOrDefault(task.id(), task.offset());
        return Math.min(task.length(), Math.max(task.offset(), liveBytes));
    }

    public static int progressPercent(UploadTask task) {
        if (task.length() <= 0L) {
            return task.state() == UploadState.COMPLETED ? 100 : 0;
        }
        return (int) Math.min(100L, uploadedBytes(task) * 100L / task.length());
    }

    public static void clear(String taskId) {
        LIVE_BYTES.remove(taskId);
    }

    public static void clearAll() {
        LIVE_BYTES.clear();
    }
}
