package com.phone2computer.transfer.core;

import java.nio.charset.StandardCharsets;
import java.util.Base64;

public final class TusMetadata {
    private TusMetadata() {
    }

    public static String create(String filename, long modifiedAt) {
        if (filename == null || filename.isBlank()) {
            throw new IllegalArgumentException("文件名不能为空");
        }
        return "filename " + encode(filename)
            + ",lastmodified " + encode(Long.toString(modifiedAt));
    }

    private static String encode(String value) {
        return Base64.getEncoder().encodeToString(value.getBytes(StandardCharsets.UTF_8));
    }
}
