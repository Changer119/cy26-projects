package com.phone2computer.transfer.core;

public final class UploadTask {
    private final String id;
    private final String contentUri;
    private final String filename;
    private final long length;
    private final long modifiedAt;
    private final String remoteUrl;
    private final long offset;
    private final UploadState state;
    private final String errorMessage;

    public UploadTask(
        String id,
        String contentUri,
        String filename,
        long length,
        long modifiedAt,
        String remoteUrl,
        long offset,
        UploadState state,
        String errorMessage
    ) {
        if (id == null || id.isBlank()) {
            throw new IllegalArgumentException("任务 ID 不能为空");
        }
        if (contentUri == null || contentUri.isBlank()) {
            throw new IllegalArgumentException("文件地址不能为空");
        }
        if (filename == null || filename.isBlank()) {
            throw new IllegalArgumentException("文件名不能为空");
        }
        if (length < 0 || offset < 0 || offset > length) {
            throw new IllegalArgumentException("文件长度或上传偏移量无效");
        }
        this.id = id;
        this.contentUri = contentUri;
        this.filename = filename;
        this.length = length;
        this.modifiedAt = modifiedAt;
        this.remoteUrl = remoteUrl == null ? "" : remoteUrl;
        this.offset = offset;
        this.state = state == null ? UploadState.PENDING : state;
        this.errorMessage = errorMessage == null ? "" : errorMessage;
    }

    public String id() { return id; }
    public String contentUri() { return contentUri; }
    public String filename() { return filename; }
    public long length() { return length; }
    public long modifiedAt() { return modifiedAt; }
    public String remoteUrl() { return remoteUrl; }
    public long offset() { return offset; }
    public UploadState state() { return state; }
    public String errorMessage() { return errorMessage; }

    public static UploadTask pending(
        String id,
        String contentUri,
        String filename,
        long length,
        long modifiedAt
    ) {
        return new UploadTask(
            id,
            contentUri,
            filename,
            length,
            modifiedAt,
            "",
            0L,
            UploadState.PENDING,
            ""
        );
    }

    public UploadTask withRemote(String nextRemoteUrl, long nextOffset) {
        return new UploadTask(
            id,
            contentUri,
            filename,
            length,
            modifiedAt,
            nextRemoteUrl,
            nextOffset,
            state,
            errorMessage
        );
    }

    public UploadTask withState(UploadState nextState, String nextErrorMessage) {
        return new UploadTask(
            id,
            contentUri,
            filename,
            length,
            modifiedAt,
            remoteUrl,
            offset,
            nextState,
            nextErrorMessage
        );
    }

    public int progressPercent() {
        if (length == 0L) {
            return 100;
        }
        return (int) Math.min(100L, offset * 100L / length);
    }
}
