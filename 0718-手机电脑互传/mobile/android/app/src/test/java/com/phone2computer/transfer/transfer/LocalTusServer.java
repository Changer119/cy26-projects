package com.phone2computer.transfer.transfer;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

final class LocalTusServer implements AutoCloseable {
    private final ServerSocket server;
    private final Thread worker;
    private volatile boolean running = true;
    private volatile String authorization = "";
    private volatile String metadata = "";
    private volatile byte[] patchedBody = new byte[0];

    LocalTusServer() throws IOException {
        server = new ServerSocket(0, 10, InetAddress.getByName("127.0.0.1"));
        worker = new Thread(this::serve, "local-tus-test-server");
        worker.start();
    }

    int port() {
        return server.getLocalPort();
    }

    String authorization() {
        return authorization;
    }

    String metadata() {
        return metadata;
    }

    byte[] patchedBody() {
        return patchedBody;
    }

    private void serve() {
        while (running) {
            try (Socket socket = server.accept()) {
                handle(socket);
            } catch (IOException error) {
                if (running) {
                    throw new IllegalStateException(error);
                }
            }
        }
    }

    private void handle(Socket socket) throws IOException {
        InputStream input = socket.getInputStream();
        String headerText = readHeaders(input);
        String[] lines = headerText.split("\r\n");
        String method = lines[0].split(" ")[0];
        Map<String, String> headers = parseHeaders(lines);
        authorization = headers.getOrDefault("authorization", "");
        metadata = headers.getOrDefault("upload-metadata", "");
        int length = Integer.parseInt(headers.getOrDefault("content-length", "0"));
        if (length > 0) {
            patchedBody = input.readNBytes(length);
        }
        writeResponse(socket.getOutputStream(), method);
    }

    private static String readHeaders(InputStream input) throws IOException {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        int matched = 0;
        int current;
        while ((current = input.read()) >= 0) {
            bytes.write(current);
            int expected = new int[] {'\r', '\n', '\r', '\n'}[matched];
            matched = current == expected ? matched + 1 : 0;
            if (matched == 4) {
                break;
            }
        }
        return bytes.toString(StandardCharsets.US_ASCII);
    }

    private static Map<String, String> parseHeaders(String[] lines) {
        Map<String, String> headers = new LinkedHashMap<>();
        for (int index = 1; index < lines.length; index++) {
            int separator = lines[index].indexOf(':');
            if (separator > 0) {
                headers.put(
                    lines[index].substring(0, separator).toLowerCase(Locale.ROOT),
                    lines[index].substring(separator + 1).trim()
                );
            }
        }
        return headers;
    }

    private static void writeResponse(OutputStream output, String method) throws IOException {
        String response = switch (method) {
            case "POST" -> "HTTP/1.1 201 Created\r\nLocation: /api/files/upload-1\r\n";
            case "HEAD" -> "HTTP/1.1 200 OK\r\nUpload-Offset: 40\r\n";
            case "PATCH" -> "HTTP/1.1 204 No Content\r\nUpload-Offset: 45\r\n";
            default -> "HTTP/1.1 405 Method Not Allowed\r\n";
        };
        output.write((response + "Content-Length: 0\r\nConnection: close\r\n\r\n")
            .getBytes(StandardCharsets.US_ASCII));
        output.flush();
    }

    @Override
    public void close() {
        running = false;
        try {
            server.close();
            worker.join(1_000L);
        } catch (Exception ignored) {
            // 测试清理阶段无需覆盖原始断言结果。
        }
    }
}
