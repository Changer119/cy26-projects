package com.phone2computer.transfer.core;

import java.net.InetAddress;
import java.net.URI;
import java.net.URLDecoder;
import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

public final class PairingConfig {
    private final String serverOrigin;
    private final String token;

    public PairingConfig(String serverOrigin, String token) {
        if (serverOrigin == null || serverOrigin.isBlank()) {
            throw new IllegalArgumentException("服务器地址不能为空");
        }
        if (token == null || token.isBlank()) {
            throw new IllegalArgumentException("配对令牌不能为空");
        }
        this.serverOrigin = serverOrigin;
        this.token = token;
    }

    public String serverOrigin() {
        return serverOrigin;
    }

    public String token() {
        return token;
    }

    public static PairingConfig parse(String value) {
        try {
            URI input = URI.create(value.trim());
            if ("phone2computer".equalsIgnoreCase(input.getScheme())) {
                Map<String, String> query = parseQuery(input.getRawQuery());
                return fromHttpUri(URI.create(required(query, "server")), required(query, "token"));
            }
            Map<String, String> query = parseQuery(input.getRawQuery());
            return fromHttpUri(input, required(query, "token"));
        } catch (RuntimeException error) {
            if (error instanceof IllegalArgumentException) {
                throw error;
            }
            throw new IllegalArgumentException("配对信息格式无效", error);
        }
    }

    public String deepLink() {
        return "phone2computer://pair?server=" + encode(serverOrigin)
            + "&token=" + encode(token);
    }

    private static PairingConfig fromHttpUri(URI uri, String token) {
        String scheme = uri.getScheme();
        if (!("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme))) {
            throw new IllegalArgumentException("只支持 HTTP 或 HTTPS 服务器");
        }
        String host = uri.getHost();
        if (host == null || !isLocalAddress(host)) {
            throw new IllegalArgumentException("服务器必须位于局域网");
        }
        int port = uri.getPort();
        String origin = scheme.toLowerCase(Locale.ROOT) + "://" + host
            + (port < 0 ? "" : ":" + port);
        return new PairingConfig(origin, token);
    }

    private static boolean isLocalAddress(String host) {
        if ("localhost".equalsIgnoreCase(host)) {
            return true;
        }
        try {
            InetAddress address = InetAddress.getByName(host);
            return address.isAnyLocalAddress()
                || address.isLoopbackAddress()
                || address.isLinkLocalAddress()
                || address.isSiteLocalAddress();
        } catch (Exception ignored) {
            return false;
        }
    }

    private static Map<String, String> parseQuery(String rawQuery) {
        Map<String, String> values = new LinkedHashMap<>();
        if (rawQuery == null || rawQuery.isBlank()) {
            return values;
        }
        for (String part : rawQuery.split("&")) {
            String[] pair = part.split("=", 2);
            if (pair.length == 2) {
                values.put(decode(pair[0]), decode(pair[1]));
            }
        }
        return values;
    }

    private static String required(Map<String, String> values, String key) {
        String value = values.get(key);
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException("缺少参数：" + key);
        }
        return value;
    }

    private static String decode(String value) {
        try {
            return URLDecoder.decode(value, StandardCharsets.UTF_8.name());
        } catch (java.io.UnsupportedEncodingException error) {
            throw new IllegalStateException(error);
        }
    }

    private static String encode(String value) {
        try {
            return URLEncoder.encode(value, StandardCharsets.UTF_8.name());
        } catch (java.io.UnsupportedEncodingException error) {
            throw new IllegalStateException(error);
        }
    }
}
