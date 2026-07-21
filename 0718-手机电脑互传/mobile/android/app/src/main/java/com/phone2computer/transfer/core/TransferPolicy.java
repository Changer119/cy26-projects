package com.phone2computer.transfer.core;

public final class TransferPolicy {
    private static final long MAX_DELAY_MILLIS = 30_000L;

    private TransferPolicy() {
    }

    public static boolean shouldRetry(int statusCode) {
        return statusCode == 408 || statusCode == 429 || statusCode >= 500;
    }

    public static long retryDelayMillis(int attempt) {
        int safeAttempt = Math.max(1, Math.min(attempt, 10));
        return Math.min(MAX_DELAY_MILLIS, 1_000L << (safeAttempt - 1));
    }
}
