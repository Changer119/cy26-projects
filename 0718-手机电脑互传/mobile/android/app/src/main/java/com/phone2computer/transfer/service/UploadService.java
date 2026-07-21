package com.phone2computer.transfer.service;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.os.SystemClock;
import com.phone2computer.transfer.core.PairingConfig;
import com.phone2computer.transfer.core.TransferPolicy;
import com.phone2computer.transfer.core.UploadState;
import com.phone2computer.transfer.core.UploadTask;
import com.phone2computer.transfer.data.PairingPreferences;
import com.phone2computer.transfer.data.UploadJournal;
import com.phone2computer.transfer.transfer.AndroidContentSource;
import com.phone2computer.transfer.transfer.PowerLocks;
import com.phone2computer.transfer.transfer.TransferEngine;
import com.phone2computer.transfer.transfer.TusClient;
import com.phone2computer.transfer.transfer.TusHttpException;
import com.phone2computer.transfer.util.FileLogger;
import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import java.util.stream.Collectors;

public final class UploadService extends Service {
    public static final String ACTION_START = "com.phone2computer.START";
    public static final String ACTION_PAUSE = "com.phone2computer.PAUSE";
    public static final String ACTION_RETRY = "com.phone2computer.RETRY";
    public static final String ACTION_STATUS = "com.phone2computer.STATUS";
    private static final String CHANNEL_ID = "file-transfer";
    private static final int NOTIFICATION_ID = 2001;
    private static final int CHUNK_BYTES = 8 * 1024 * 1024;
    private static final int CONCURRENCY = 6;
    private static final long PROGRESS_REFRESH_MILLIS = 250L;
    private final AtomicBoolean runScheduled = new AtomicBoolean(false);
    private final AtomicLong lastProgressRefresh = new AtomicLong(0L);
    private final ExecutorService coordinator = Executors.newSingleThreadExecutor();
    private volatile boolean enabled;
    private UploadJournal journal;
    private PairingPreferences pairingPreferences;
    private TransferEngine engine;
    private PowerLocks powerLocks;
    private FileLogger logger;

    @Override
    public void onCreate() {
        super.onCreate();
        journal = new UploadJournal(new File(getFilesDir(), "uploads/tasks.journal"));
        pairingPreferences = new PairingPreferences(this);
        engine = new TransferEngine(
            journal,
            new TusClient(),
            new AndroidContentSource(getContentResolver()),
            CHUNK_BYTES
        );
        powerLocks = new PowerLocks(this);
        logger = new FileLogger(this);
        UploadProgressRegistry.clearAll();
        createNotificationChannel();
        try {
            journal.pauseActive();
        } catch (IOException error) {
            logger.error("恢复中断任务失败", error);
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        startForeground(NOTIFICATION_ID, buildNotification());
        String action = intent == null ? ACTION_START : intent.getAction();
        if (ACTION_PAUSE.equals(action)) {
            pauseTransfers();
            return START_STICKY;
        }
        enabled = true;
        try {
            if (ACTION_RETRY.equals(action)) {
                journal.retryFailed();
            }
            journal.resumePaused();
            scheduleRun();
        } catch (IOException error) {
            logger.error("启动任务队列失败", error);
            stopSelf();
        }
        return START_STICKY;
    }

    private void scheduleRun() {
        if (!runScheduled.compareAndSet(false, true)) {
            return;
        }
        coordinator.execute(() -> {
            try {
                drainQueue();
            } finally {
                runScheduled.set(false);
                if (enabled && hasPendingTasks()) {
                    scheduleRun();
                } else {
                    powerLocks.release();
                    stopForeground(STOP_FOREGROUND_REMOVE);
                    stopSelf();
                }
            }
        });
    }

    private void drainQueue() {
        Optional<PairingConfig> pairing = pairingPreferences.load();
        if (pairing.isEmpty()) {
            logger.info("没有配对信息，停止上传");
            return;
        }
        powerLocks.acquire();
        while (enabled) {
            List<UploadTask> pending = pendingTasks();
            if (pending.isEmpty()) {
                break;
            }
            ExecutorService workers = Executors.newFixedThreadPool(CONCURRENCY);
            List<Future<?>> futures = new ArrayList<>();
            for (UploadTask task : pending) {
                futures.add(workers.submit(() -> processTask(pairing.get(), task)));
            }
            workers.shutdown();
            waitFor(futures);
        }
        publishStatus();
    }

    private void processTask(PairingConfig pairing, UploadTask task) {
        int attempt = 0;
        while (enabled) {
            attempt++;
            try {
                engine.upload(
                    pairing,
                    latest(task.id()).orElse(task),
                    () -> enabled,
                    uploadedBytes -> reportProgress(task.id(), uploadedBytes)
                );
                UploadProgressRegistry.clear(task.id());
                logger.info("上传完成：" + task.filename());
                publishStatus();
                return;
            } catch (IOException error) {
                UploadProgressRegistry.clear(task.id());
                if (!enabled) {
                    mark(task.id(), UploadState.PAUSED, "");
                    publishStatus();
                    return;
                }
                if (!shouldRetry(error) || attempt >= 5) {
                    mark(task.id(), UploadState.FAILED, readableMessage(error));
                    logger.error("上传失败：" + task.filename(), error);
                    publishStatus();
                    return;
                }
                sleepBeforeRetry(attempt);
            }
        }
    }

    private void reportProgress(String taskId, long uploadedBytes) {
        UploadProgressRegistry.update(taskId, uploadedBytes);
        long now = SystemClock.elapsedRealtime();
        long previous = lastProgressRefresh.get();
        if (
            now - previous >= PROGRESS_REFRESH_MILLIS
                && lastProgressRefresh.compareAndSet(previous, now)
        ) {
            publishStatus();
        }
    }

    private void pauseTransfers() {
        enabled = false;
        try {
            journal.pauseActive();
            logger.info("用户暂停全部上传");
        } catch (IOException error) {
            logger.error("暂停任务失败", error);
        }
        publishStatus();
    }

    private List<UploadTask> pendingTasks() {
        try {
            return journal.list().stream()
                .filter(task -> task.state() == UploadState.PENDING)
                .collect(Collectors.toList());
        } catch (IOException error) {
            logger.error("读取任务队列失败", error);
            return List.of();
        }
    }

    private boolean hasPendingTasks() {
        return !pendingTasks().isEmpty();
    }

    private Optional<UploadTask> latest(String id) {
        try {
            return journal.list().stream().filter(task -> task.id().equals(id)).findFirst();
        } catch (IOException error) {
            return Optional.empty();
        }
    }

    private void mark(String id, UploadState state, String message) {
        latest(id).ifPresent(task -> {
            try {
                journal.save(task.withState(state, message));
            } catch (IOException error) {
                logger.error("保存任务状态失败", error);
            }
        });
    }

    private static boolean shouldRetry(IOException error) {
        return !(error instanceof TusHttpException httpError)
            || TransferPolicy.shouldRetry(httpError.statusCode());
    }

    private static String readableMessage(IOException error) {
        String message = error.getMessage();
        return message == null || message.isBlank() ? "传输失败" : message;
    }

    private void sleepBeforeRetry(int attempt) {
        try {
            Thread.sleep(TransferPolicy.retryDelayMillis(attempt));
        } catch (InterruptedException error) {
            Thread.currentThread().interrupt();
            enabled = false;
        }
    }

    private static void waitFor(List<Future<?>> futures) {
        for (Future<?> future : futures) {
            try {
                future.get();
            } catch (Exception ignored) {
                // 单任务已在 processTask 内记录失败状态。
            }
        }
    }

    private void publishStatus() {
        getSystemService(NotificationManager.class).notify(NOTIFICATION_ID, buildNotification());
        sendBroadcast(new Intent(ACTION_STATUS).setPackage(getPackageName()));
    }

    private Notification buildNotification() {
        List<UploadTask> tasks;
        try {
            tasks = journal == null ? List.of() : journal.list();
        } catch (IOException ignored) {
            tasks = List.of();
        }
        int completed = (int) tasks.stream()
            .filter(task -> task.state() == UploadState.COMPLETED)
            .count();
        long totalBytes = tasks.stream().mapToLong(UploadTask::length).sum();
        long uploadedBytes = tasks.stream()
            .mapToLong(UploadProgressRegistry::uploadedBytes)
            .sum();
        int progress = totalBytes == 0L
            ? 0
            : (int) Math.min(100L, uploadedBytes * 100L / totalBytes);
        PendingIntent pause = PendingIntent.getService(
            this,
            1,
            new Intent(this, UploadService.class).setAction(ACTION_PAUSE),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );
        return new Notification.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.stat_sys_upload)
            .setContentTitle("Phone2Computer 正在传输")
            .setContentText(
                completed + " / " + tasks.size() + " 个文件已完成 · " + progress + "%"
            )
            .setOngoing(enabled)
            .setOnlyAlertOnce(true)
            .setProgress(100, progress, tasks.isEmpty())
            .addAction(new Notification.Action.Builder(null, "暂停", pause).build())
            .build();
    }

    private void createNotificationChannel() {
        NotificationChannel channel = new NotificationChannel(
            CHANNEL_ID,
            "文件传输",
            NotificationManager.IMPORTANCE_LOW
        );
        channel.setDescription("显示后台照片和视频传输进度");
        getSystemService(NotificationManager.class).createNotificationChannel(channel);
    }

    @Override
    public void onTimeout(int startId, int foregroundServiceType) {
        enabled = false;
        pauseTransfers();
        stopSelf();
    }

    @Override
    public void onDestroy() {
        enabled = false;
        coordinator.shutdownNow();
        UploadProgressRegistry.clearAll();
        powerLocks.release();
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
