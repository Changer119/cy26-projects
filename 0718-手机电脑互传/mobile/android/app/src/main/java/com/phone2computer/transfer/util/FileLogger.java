package com.phone2computer.transfer.util;

import android.content.Context;
import android.util.Log;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;
import java.time.Instant;

public final class FileLogger {
    private static final String TAG = "Phone2Computer";
    private final File logFile;

    public FileLogger(Context context) {
        File directory = new File(context.getFilesDir(), "logs");
        if (!directory.exists()) {
            directory.mkdirs();
        }
        logFile = new File(directory, "mobile.log");
    }

    public synchronized void info(String message) {
        Log.i(TAG, message);
        append("INFO", message);
    }

    public synchronized void error(String message, Throwable error) {
        Log.e(TAG, message, error);
        append("ERROR", message + " | " + error.getClass().getSimpleName() + ": " + error.getMessage());
    }

    private void append(String level, String message) {
        String line = Instant.now() + " " + level + " " + message + System.lineSeparator();
        try (FileOutputStream output = new FileOutputStream(logFile, true)) {
            output.write(line.getBytes(StandardCharsets.UTF_8));
        } catch (Exception error) {
            Log.e(TAG, "无法写入文件日志", error);
        }
    }
}
