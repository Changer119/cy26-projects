package com.phone2computer.transfer.transfer;

import com.phone2computer.transfer.core.PairingConfig;
import com.phone2computer.transfer.core.UploadState;
import com.phone2computer.transfer.core.UploadTask;
import com.phone2computer.transfer.data.UploadJournal;
import java.io.IOException;
import java.util.function.BooleanSupplier;
import java.util.function.LongConsumer;

public final class TransferEngine {
    private final UploadJournal journal;
    private final TusTransport transport;
    private final ContentSource source;
    private final int chunkLength;

    public TransferEngine(
        UploadJournal journal,
        TusTransport transport,
        ContentSource source,
        int chunkLength
    ) {
        if (chunkLength <= 0) {
            throw new IllegalArgumentException("分片大小必须大于零");
        }
        this.journal = journal;
        this.transport = transport;
        this.source = source;
        this.chunkLength = chunkLength;
    }

    public UploadTask upload(
        PairingConfig pairing,
        UploadTask original,
        BooleanSupplier shouldContinue
    ) throws IOException {
        return upload(pairing, original, shouldContinue, ignored -> { });
    }

    public UploadTask upload(
        PairingConfig pairing,
        UploadTask original,
        BooleanSupplier shouldContinue,
        LongConsumer onProgress
    ) throws IOException {
        UploadTask current = original.withState(UploadState.UPLOADING, "");
        journal.save(current);

        if (current.remoteUrl().isBlank()) {
            String remoteUrl = transport.create(pairing, current);
            current = current.withRemote(remoteUrl, 0L);
            journal.save(current);
        }

        long serverOffset = transport.queryOffset(pairing, current.remoteUrl());
        if (serverOffset < 0 || serverOffset > current.length()) {
            throw new IOException("Mac 返回的断点位置超出文件范围");
        }
        current = current.withRemote(current.remoteUrl(), serverOffset);
        journal.save(current);
        onProgress.accept(serverOffset);

        while (current.offset() < current.length()) {
            if (!shouldContinue.getAsBoolean()) {
                current = current.withState(UploadState.PAUSED, "");
                journal.save(current);
                return current;
            }
            int requested = (int) Math.min(
                chunkLength,
                current.length() - current.offset()
            );
            byte[] bytes = source.read(current.contentUri(), current.offset(), requested);
            if (bytes.length == 0 || bytes.length > requested) {
                throw new IOException("无法从手机读取完整文件分片");
            }
            long chunkOffset = current.offset();
            long nextOffset = transport.append(
                pairing,
                current.remoteUrl(),
                chunkOffset,
                bytes,
                sentBytes -> onProgress.accept(chunkOffset + sentBytes)
            );
            if (nextOffset != current.offset() + bytes.length) {
                throw new IOException("Mac 返回的分片偏移量不一致");
            }
            current = current.withRemote(current.remoteUrl(), nextOffset);
            journal.save(current);
        }

        current = current.withState(UploadState.COMPLETED, "");
        journal.save(current);
        return current;
    }
}
