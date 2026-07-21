package com.phone2computer.transfer.transfer;

import com.phone2computer.transfer.core.PairingConfig;
import com.phone2computer.transfer.core.UploadTask;
import java.io.IOException;
import java.util.function.LongConsumer;

public interface TusTransport {
    String create(PairingConfig pairing, UploadTask task) throws IOException;

    long queryOffset(PairingConfig pairing, String uploadUrl) throws IOException;

    long append(
        PairingConfig pairing,
        String uploadUrl,
        long offset,
        byte[] bytes,
        LongConsumer onBytesSent
    ) throws IOException;
}
