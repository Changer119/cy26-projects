package com.phone2computer.transfer.data;

import com.phone2computer.transfer.core.UploadState;
import com.phone2computer.transfer.core.UploadTask;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.EOFException;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.CRC32;

public final class UploadJournal {
    private static final int FORMAT_VERSION = 1;
    private static final int MAX_RECORD_BYTES = 1_048_576;
    private static final Object FILE_LOCK = new Object();
    private final File file;

    public UploadJournal(File file) {
        this.file = file;
    }

    public void save(UploadTask task) throws IOException {
        synchronized (FILE_LOCK) {
            saveLocked(task);
        }
    }

    private void saveLocked(UploadTask task) throws IOException {
        byte[] payload = encode(task);
        File parent = file.getParentFile();
        if (parent != null && !parent.exists() && !parent.mkdirs()) {
            throw new IOException("无法创建任务存储目录");
        }
        CRC32 checksum = new CRC32();
        checksum.update(payload);
        try (
            FileOutputStream fileOutput = new FileOutputStream(file, true);
            DataOutputStream output = new DataOutputStream(fileOutput)
        ) {
            output.writeInt(payload.length);
            output.write(payload);
            output.writeLong(checksum.getValue());
            output.flush();
            fileOutput.getFD().sync();
        }
    }

    public List<UploadTask> list() throws IOException {
        synchronized (FILE_LOCK) {
            return listLocked();
        }
    }

    private List<UploadTask> listLocked() throws IOException {
        Map<String, UploadTask> newest = new LinkedHashMap<>();
        if (!file.exists() || file.length() == 0L) {
            return new ArrayList<>();
        }
        try (DataInputStream input = new DataInputStream(new FileInputStream(file))) {
            while (readNext(input, newest)) {
                // 持续重放记录，直到文件正常结束或遇到损坏尾部。
            }
        }
        return new ArrayList<>(newest.values());
    }

    public void retryFailed() throws IOException {
        synchronized (FILE_LOCK) {
            for (UploadTask task : listLocked()) {
                if (task.state() == UploadState.FAILED) {
                    saveLocked(task.withState(UploadState.PENDING, ""));
                }
            }
        }
    }

    public void pauseActive() throws IOException {
        synchronized (FILE_LOCK) {
            for (UploadTask task : listLocked()) {
                if (task.state() == UploadState.PENDING || task.state() == UploadState.UPLOADING) {
                    saveLocked(task.withState(UploadState.PAUSED, ""));
                }
            }
        }
    }

    public void resumePaused() throws IOException {
        synchronized (FILE_LOCK) {
            for (UploadTask task : listLocked()) {
                if (task.state() == UploadState.PAUSED) {
                    saveLocked(task.withState(UploadState.PENDING, ""));
                }
            }
        }
    }

    private static boolean readNext(
        DataInputStream input,
        Map<String, UploadTask> newest
    ) throws IOException {
        try {
            int length = input.readInt();
            if (length <= 0 || length > MAX_RECORD_BYTES) {
                return false;
            }
            byte[] payload = new byte[length];
            input.readFully(payload);
            long expectedChecksum = input.readLong();
            CRC32 checksum = new CRC32();
            checksum.update(payload);
            if (checksum.getValue() != expectedChecksum) {
                return false;
            }
            UploadTask task = decode(payload);
            newest.put(task.id(), task);
            return true;
        } catch (EOFException ignored) {
            return false;
        } catch (IllegalArgumentException ignored) {
            return false;
        }
    }

    private static byte[] encode(UploadTask task) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        try (DataOutputStream output = new DataOutputStream(bytes)) {
            output.writeInt(FORMAT_VERSION);
            output.writeUTF(task.id());
            output.writeUTF(task.contentUri());
            output.writeUTF(task.filename());
            output.writeLong(task.length());
            output.writeLong(task.modifiedAt());
            output.writeUTF(task.remoteUrl());
            output.writeLong(task.offset());
            output.writeUTF(task.state().name());
            output.writeUTF(task.errorMessage());
        }
        return bytes.toByteArray();
    }

    private static UploadTask decode(byte[] payload) throws IOException {
        try (DataInputStream input = new DataInputStream(new ByteArrayInputStream(payload))) {
            int version = input.readInt();
            if (version != FORMAT_VERSION) {
                throw new IOException("不支持的任务存储版本");
            }
            return new UploadTask(
                input.readUTF(),
                input.readUTF(),
                input.readUTF(),
                input.readLong(),
                input.readLong(),
                input.readUTF(),
                input.readLong(),
                UploadState.valueOf(input.readUTF()),
                input.readUTF()
            );
        }
    }
}
