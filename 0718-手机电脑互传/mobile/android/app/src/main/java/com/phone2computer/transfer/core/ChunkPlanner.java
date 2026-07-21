package com.phone2computer.transfer.core;

public final class ChunkPlanner {
    private ChunkPlanner() {
    }

    public static long nextLength(long offset, long totalLength, long chunkLength) {
        if (offset < 0 || totalLength < 0 || offset > totalLength) {
            throw new IllegalArgumentException("上传偏移量无效");
        }
        if (chunkLength <= 0) {
            throw new IllegalArgumentException("分片大小必须大于零");
        }
        return Math.min(totalLength - offset, chunkLength);
    }
}
