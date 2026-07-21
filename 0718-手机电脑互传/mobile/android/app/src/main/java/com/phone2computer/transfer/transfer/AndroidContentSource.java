package com.phone2computer.transfer.transfer;

import android.content.ContentResolver;
import android.content.res.AssetFileDescriptor;
import android.net.Uri;
import java.io.ByteArrayOutputStream;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.util.Arrays;

public final class AndroidContentSource implements ContentSource {
    private final ContentResolver resolver;

    public AndroidContentSource(ContentResolver resolver) {
        this.resolver = resolver;
    }

    @Override
    public byte[] read(String contentUri, long offset, int maximumLength) throws IOException {
        Uri uri = Uri.parse(contentUri);
        try {
            return readSeekable(uri, offset, maximumLength);
        } catch (Exception ignored) {
            return readBySkipping(uri, offset, maximumLength);
        }
    }

    private byte[] readSeekable(Uri uri, long offset, int maximumLength) throws IOException {
        try (AssetFileDescriptor descriptor = resolver.openAssetFileDescriptor(uri, "r")) {
            if (descriptor == null) {
                throw new IOException("无法打开文件");
            }
            try (FileInputStream input = new FileInputStream(descriptor.getFileDescriptor())) {
                FileChannel channel = input.getChannel();
                channel.position(descriptor.getStartOffset() + offset);
                ByteBuffer buffer = ByteBuffer.allocate(maximumLength);
                while (buffer.hasRemaining() && channel.read(buffer) >= 0) {
                    // 读取到分片已满或文件结束。
                }
                return Arrays.copyOf(buffer.array(), buffer.position());
            }
        }
    }

    private byte[] readBySkipping(Uri uri, long offset, int maximumLength) throws IOException {
        try (InputStream input = resolver.openInputStream(uri)) {
            if (input == null) {
                throw new IOException("无法打开文件");
            }
            skipFully(input, offset);
            ByteArrayOutputStream bytes = new ByteArrayOutputStream(maximumLength);
            byte[] buffer = new byte[Math.min(65_536, maximumLength)];
            while (bytes.size() < maximumLength) {
                int requested = Math.min(buffer.length, maximumLength - bytes.size());
                int count = input.read(buffer, 0, requested);
                if (count < 0) {
                    break;
                }
                bytes.write(buffer, 0, count);
            }
            return bytes.toByteArray();
        }
    }

    private static void skipFully(InputStream input, long offset) throws IOException {
        long remaining = offset;
        while (remaining > 0L) {
            long skipped = input.skip(remaining);
            if (skipped > 0L) {
                remaining -= skipped;
            } else if (input.read() >= 0) {
                remaining--;
            } else {
                throw new IOException("文件长度短于断点位置");
            }
        }
    }
}
