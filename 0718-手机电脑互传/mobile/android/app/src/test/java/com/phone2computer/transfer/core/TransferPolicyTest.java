package com.phone2computer.transfer.core;

import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

public final class TransferPolicyTest {
    @Test
    public void retriesTimeoutRateLimitAndServerErrors() {
        assertTrue(TransferPolicy.shouldRetry(408));
        assertTrue(TransferPolicy.shouldRetry(429));
        assertTrue(TransferPolicy.shouldRetry(503));
    }

    @Test
    public void doesNotRetryAuthenticationOrProtocolErrors() {
        assertFalse(TransferPolicy.shouldRetry(401));
        assertFalse(TransferPolicy.shouldRetry(409));
    }

    @Test
    public void retryDelayIsBoundedExponentialBackoff() {
        assertTrue(TransferPolicy.retryDelayMillis(1) < TransferPolicy.retryDelayMillis(3));
        assertTrue(TransferPolicy.retryDelayMillis(20) <= 30_000L);
    }
}
