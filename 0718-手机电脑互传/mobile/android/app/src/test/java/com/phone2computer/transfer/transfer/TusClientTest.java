package com.phone2computer.transfer.transfer;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertTrue;

import com.phone2computer.transfer.core.PairingConfig;
import com.phone2computer.transfer.core.UploadTask;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import org.junit.After;
import org.junit.Before;
import org.junit.Test;

public final class TusClientTest {
    private LocalTusServer server;
    private PairingConfig pairing;

    @Before
    public void startServer() throws Exception {
        server = new LocalTusServer();
        pairing = PairingConfig.parse(
            "http://127.0.0.1:" + server.port() + "/?token=test-token"
        );
    }

    @After
    public void stopServer() {
        server.close();
    }

    @Test
    public void createsUploadWithAuthorizationAndMetadata() throws Exception {
        UploadTask task = UploadTask.pending("1", "content://a", "旅行.mp4", 100L, 123L);

        String url = new TusClient().create(pairing, task);

        assertEquals(pairing.serverOrigin() + "/api/files/upload-1", url);
        assertEquals("Bearer test-token", server.authorization());
        org.junit.Assert.assertTrue(server.metadata().startsWith("filename "));
    }

    @Test
    public void readsPersistedServerOffset() throws Exception {
        long offset = new TusClient().queryOffset(
            pairing,
            pairing.serverOrigin() + "/api/files/upload-1"
        );

        assertEquals(40L, offset);
    }

    @Test
    public void patchesChunkAtExpectedOffset() throws Exception {
        byte[] bytes = "hello".getBytes(StandardCharsets.UTF_8);

        long nextOffset = new TusClient().append(
            pairing,
            pairing.serverOrigin() + "/api/files/upload-1",
            40L,
            bytes,
            ignored -> { }
        );

        assertEquals(45L, nextOffset);
        assertArrayEquals(bytes, server.patchedBody());
    }

    @Test
    public void reportsProgressWhileWritingChunk() throws Exception {
        byte[] bytes = new byte[200_000];
        List<Long> progress = new ArrayList<>();

        new TusClient().append(
            pairing,
            pairing.serverOrigin() + "/api/files/upload-1",
            40L,
            bytes,
            progress::add
        );

        assertTrue(progress.size() > 1);
        assertEquals(bytes.length, progress.get(progress.size() - 1).longValue());
    }
}
