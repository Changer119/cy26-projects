package com.phone2computer.transfer.transfer;

import com.phone2computer.transfer.core.PairingConfig;
import com.phone2computer.transfer.core.TusMetadata;
import com.phone2computer.transfer.core.UploadTask;
import java.io.IOException;
import java.net.URI;
import java.util.concurrent.TimeUnit;
import java.util.function.LongConsumer;
import okhttp3.MediaType;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;
import okio.BufferedSink;

public final class TusClient implements TusTransport {
    private static final String TUS_VERSION = "1.0.0";
    private static final int WRITE_BUFFER_BYTES = 64 * 1024;
    private static final MediaType CHUNK_TYPE = MediaType.get("application/offset+octet-stream");
    private final OkHttpClient httpClient;

    public TusClient() {
        httpClient = new OkHttpClient.Builder()
            .connectTimeout(15L, TimeUnit.SECONDS)
            .readTimeout(30L, TimeUnit.SECONDS)
            .writeTimeout(60L, TimeUnit.SECONDS)
            .retryOnConnectionFailure(true)
            .build();
    }

    @Override
    public String create(PairingConfig pairing, UploadTask task) throws IOException {
        Request request = baseRequest(pairing, pairing.serverOrigin() + "/api/files/")
            .header("Upload-Length", Long.toString(task.length()))
            .header("Upload-Metadata", TusMetadata.create(task.filename(), task.modifiedAt()))
            .post(RequestBody.create(new byte[0], CHUNK_TYPE))
            .build();
        try (Response response = httpClient.newCall(request).execute()) {
            requireStatus(response, 201);
            String location = response.header("Location");
            if (location == null || location.isBlank()) {
                throw new IOException("Mac 未返回上传地址");
            }
            return URI.create(pairing.serverOrigin() + "/").resolve(location).toString();
        }
    }

    @Override
    public long queryOffset(PairingConfig pairing, String uploadUrl) throws IOException {
        Request request = baseRequest(pairing, uploadUrl).head().build();
        try (Response response = httpClient.newCall(request).execute()) {
            requireStatus(response, 200);
            return parseOffset(response);
        }
    }

    @Override
    public long append(
        PairingConfig pairing,
        String uploadUrl,
        long offset,
        byte[] bytes,
        LongConsumer onBytesSent
    ) throws IOException {
        Request request = baseRequest(pairing, uploadUrl)
            .header("Upload-Offset", Long.toString(offset))
            .patch(progressBody(bytes, onBytesSent))
            .build();
        try (Response response = httpClient.newCall(request).execute()) {
            requireStatus(response, 204);
            return parseOffset(response);
        }
    }

    private static RequestBody progressBody(byte[] bytes, LongConsumer onBytesSent) {
        return new RequestBody() {
            @Override
            public MediaType contentType() {
                return CHUNK_TYPE;
            }

            @Override
            public long contentLength() {
                return bytes.length;
            }

            @Override
            public void writeTo(BufferedSink sink) throws IOException {
                int sent = 0;
                while (sent < bytes.length) {
                    int count = Math.min(WRITE_BUFFER_BYTES, bytes.length - sent);
                    sink.write(bytes, sent, count);
                    sent += count;
                    onBytesSent.accept(sent);
                }
            }
        };
    }

    private static Request.Builder baseRequest(PairingConfig pairing, String url) {
        return new Request.Builder()
            .url(url)
            .header("Authorization", "Bearer " + pairing.token())
            .header("Tus-Resumable", TUS_VERSION);
    }

    private static long parseOffset(Response response) throws IOException {
        String value = response.header("Upload-Offset");
        try {
            return Long.parseLong(value == null ? "" : value);
        } catch (NumberFormatException error) {
            throw new IOException("Mac 返回的上传偏移量无效", error);
        }
    }

    private static void requireStatus(Response response, int expected) throws IOException {
        if (response.code() == expected) {
            return;
        }
        String message = response.body() == null ? "" : response.body().string();
        throw new TusHttpException(response.code(), "上传协议错误：" + message);
    }
}
