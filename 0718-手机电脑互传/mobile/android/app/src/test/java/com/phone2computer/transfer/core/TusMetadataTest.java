package com.phone2computer.transfer.core;

import static org.junit.Assert.assertEquals;

import java.nio.charset.StandardCharsets;
import java.util.Base64;
import org.junit.Test;

public final class TusMetadataTest {
    @Test
    public void encodesUnicodeFilenameAndModifiedTime() {
        String header = TusMetadata.create("旅行 视频.mp4", 1721260800123L);

        String filename = Base64.getEncoder().encodeToString(
            "旅行 视频.mp4".getBytes(StandardCharsets.UTF_8)
        );
        String modified = Base64.getEncoder().encodeToString(
            "1721260800123".getBytes(StandardCharsets.UTF_8)
        );
        assertEquals(
            "filename " + filename + ",lastmodified " + modified,
            header
        );
    }
}
