package com.phone2computer.transfer.transfer;

import static org.junit.Assert.assertEquals;

import com.phone2computer.transfer.core.PairingConfig;
import com.phone2computer.transfer.core.UploadState;
import com.phone2computer.transfer.core.UploadTask;
import com.phone2computer.transfer.data.UploadJournal;
import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

public final class TransferEngineTest {
    @Rule
    public TemporaryFolder temporaryFolder = new TemporaryFolder();

    @Test
    public void resumesFromOffsetReportedByMac() throws Exception {
        File file = temporaryFolder.newFile("tasks.journal");
        UploadJournal journal = new UploadJournal(file);
        UploadTask task = UploadTask.pending("1", "content://video", "video.mp4", 10L, 1L)
            .withRemote("http://127.0.0.1/api/files/1", 2L);
        RecordingSource source = new RecordingSource(new byte[10]);
        RecordingTransport transport = new RecordingTransport(4L);
        TransferEngine engine = new TransferEngine(journal, transport, source, 3);
        List<Long> progress = new ArrayList<>();

        UploadTask completed = engine.upload(pairing(), task, () -> true, progress::add);

        assertEquals(List.of(4L, 7L), source.readOffsets);
        assertEquals(List.of(4L, 7L, 10L), progress);
        assertEquals(UploadState.COMPLETED, completed.state());
        assertEquals(10L, journal.list().get(0).offset());
    }

    @Test
    public void createsRemoteUploadOnlyOnce() throws Exception {
        File file = temporaryFolder.newFile("tasks.journal");
        UploadJournal journal = new UploadJournal(file);
        RecordingTransport transport = new RecordingTransport(0L);
        TransferEngine engine = new TransferEngine(
            journal,
            transport,
            new RecordingSource(new byte[] {1, 2}),
            8
        );

        engine.upload(
            pairing(),
            UploadTask.pending("1", "content://photo", "photo.jpg", 2L, 1L),
            () -> true
        );

        assertEquals(1, transport.createCalls);
        assertEquals(1, transport.appendedChunks.size());
    }

    private static PairingConfig pairing() {
        return PairingConfig.parse("http://127.0.0.1:18765/?token=test");
    }

    private static final class RecordingSource implements ContentSource {
        private final byte[] bytes;
        private final List<Long> readOffsets = new ArrayList<>();

        private RecordingSource(byte[] bytes) {
            this.bytes = bytes;
        }

        @Override
        public byte[] read(String contentUri, long offset, int maximumLength) {
            readOffsets.add(offset);
            int start = Math.toIntExact(offset);
            int end = Math.min(bytes.length, start + maximumLength);
            return Arrays.copyOfRange(bytes, start, end);
        }
    }

    private static final class RecordingTransport implements TusTransport {
        private final long serverOffset;
        private int createCalls;
        private final List<byte[]> appendedChunks = new ArrayList<>();

        private RecordingTransport(long serverOffset) {
            this.serverOffset = serverOffset;
        }

        @Override
        public String create(PairingConfig pairing, UploadTask task) {
            createCalls++;
            return pairing.serverOrigin() + "/api/files/created";
        }

        @Override
        public long queryOffset(PairingConfig pairing, String uploadUrl) {
            return serverOffset;
        }

        @Override
        public long append(
            PairingConfig pairing,
            String uploadUrl,
            long offset,
            byte[] bytes,
            java.util.function.LongConsumer onBytesSent
        ) {
            appendedChunks.add(bytes);
            onBytesSent.accept(bytes.length);
            return offset + bytes.length;
        }
    }
}
