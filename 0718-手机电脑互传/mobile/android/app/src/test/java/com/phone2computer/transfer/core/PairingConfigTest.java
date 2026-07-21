package com.phone2computer.transfer.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertThrows;

import org.junit.Test;

public final class PairingConfigTest {
    @Test
    public void parsesBrowserPairingUrl() {
        PairingConfig config = PairingConfig.parse(
            "http://192.168.3.20:18765/?token=secret-token"
        );

        assertEquals("http://192.168.3.20:18765", config.serverOrigin());
        assertEquals("secret-token", config.token());
    }

    @Test
    public void parsesAppDeepLink() {
        PairingConfig config = PairingConfig.parse(
            "phone2computer://pair?server=http%3A%2F%2F192.168.3.20%3A18765&token=abc"
        );

        assertEquals("http://192.168.3.20:18765", config.serverOrigin());
        assertEquals("abc", config.token());
    }

    @Test
    public void rejectsMissingToken() {
        assertThrows(
            IllegalArgumentException.class,
            () -> PairingConfig.parse("http://192.168.3.20:18765/")
        );
    }

    @Test
    public void rejectsPublicInternetHost() {
        assertThrows(
            IllegalArgumentException.class,
            () -> PairingConfig.parse("https://example.com/?token=abc")
        );
    }
}
